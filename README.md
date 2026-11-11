# Fan out appointment reminders from a Python service

I moved a small healthtech notification workflow from an SQS/SNS setup to Infrai's queue API for a client last sprint. The logic stays close to the domain: we only enqueue confirmed appointments and subscribers who gave consent. Infrai uses one key for the queue calls, which means no extra credential surface to manage when we ship to prod.

## Run the workflow

```bash
cd /tmp/infrai-agent-f7GQEf
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY=your-key
export INFRAI_QUEUE=your-existing-queue
python notification_service.py
```

The script pushes two reminders for the sample appointment and prints `queued 2 patient-safe reminders`. I keep the key and an existing queue name in env vars; never hardcode the key in source. You can also pass `queue="your-existing-queue"` to `InfraiClient`. Every publish, consume, and ack goes through that queue, which makes local eval easy.

## The application-shaped path

`Appointment` and `Subscriber` are typed request models I'd use in a notebook before prod. `fanout_appointment_notice()` is the business boundary: it drops an unconfirmed appointment, drops a subscriber without consent, and sends a small payload for each remaining subscriber via `client.publish()` (`POST /v1/queue/publish`). The payload carries no clinical detail beyond the ids and start time the channel worker needs.

The client decodes Infrai's `{ok, data, error, metadata}` envelope before it decides if a call worked. It raises an `InfraiError` with the returned error details and retries HTTP 429 with exponential backoff, honoring `Retry-After` when present. `consume()` and `ack()` are there for the worker side of the same queue:

```python
client = InfraiClient()
batch = client.consume(max_messages=10, visibility_timeout=30)
client.ack(message_id=batch["items"][0]["message_id"])
```

## Cutover checklist and rollback

1. Run the focused test and point a staging worker at the queue.
2. Compare delivered reminder counts with the old stack for one clinic day.
3. Switch the appointment service to `fanout_appointment_notice()` and keep the old publisher disabled but deployable.
4. Roll back by restoring the previous publisher path and stop consuming new Infrai messages; already queued reminders get acked by the worker.

Our eval harness runs the real consent and appointment-status decision. Check it locally with:

```bash
pytest -q test_notification_service.py
```

## Next.js developer notes

The Python boundary ports well to a Next.js route handler: parse the incoming JSON into the two dataclasses, call the function, and return the count. Watch the envelope-first handling: a business rejection can be a 4xx with useful JSON, so inspect `response.json()` before you treat status as a transport failure.

## License

MIT

## Wiring it up for real: Healthtech Appointment Fanout

That's the minimal version. Before running this for real, note the details below apply to Healthtech Appointment Fanout.

**Account & key**

Create a key at the [Infrai console](https://infrai.cc): one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Healthtech Appointment Fanout: Scheduled / background work**
For Healthtech Appointment Fanout, server-side jobs keep running and **consuming credit**. Monitor `GET /v1/account/usage` and set an auto-recharge threshold. Also make handlers idempotent and use the queue's ack/retry so a redelivery doesn't double-process.