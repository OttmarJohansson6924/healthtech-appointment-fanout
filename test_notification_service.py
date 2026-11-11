from notification_service import Appointment, Subscriber, fanout_appointment_notice


class RecordingClient:
    def __init__(self):
        self.payloads = []

    def publish(self, payload):
        self.payloads.append(payload)
        return {"message_id": f"m-{len(self.payloads)}"}


def test_only_consented_subscribers_receive_confirmed_appointment_notice():
    client = RecordingClient()
    appointment = Appointment("apt-1", "patient-1", "2026-10-02T09:30:00Z", "confirmed")
    subscribers = [Subscriber("s1", "sms", True), Subscriber("s2", "email", False)]

    assert fanout_appointment_notice(appointment, subscribers, client) == 1
    assert client.payloads == [{
        "event": "appointment_reminder",
        "appointment_id": "apt-1",
        "patient_id": "patient-1",
        "starts_at": "2026-10-02T09:30:00Z",
        "subscriber_id": "s1",
        "channel": "sms",
    }]
