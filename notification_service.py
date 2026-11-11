from dataclasses import dataclass
from typing import Iterable

from infrai_client import InfraiClient


@dataclass(frozen=True)
class Appointment:
    appointment_id: str
    patient_id: str
    starts_at: str
    status: str


@dataclass(frozen=True)
class Subscriber:
    subscriber_id: str
    channel: str
    consented: bool


def fanout_appointment_notice(
    appointment: Appointment, subscribers: Iterable[Subscriber], client: InfraiClient
) -> int:
    """Publish a minimal reminder only for confirmed appointments and opted-in subscribers."""
    if appointment.status != "confirmed":
        return 0
    sent = 0
    for subscriber in subscribers:
        if not subscriber.consented:
            continue
        client.publish(
            {
                "event": "appointment_reminder",
                "appointment_id": appointment.appointment_id,
                "patient_id": appointment.patient_id,
                "starts_at": appointment.starts_at,
                "subscriber_id": subscriber.subscriber_id,
                "channel": subscriber.channel,
            }
        )
        sent += 1
    return sent


if __name__ == "__main__":
    appointment = Appointment("apt-204", "patient-17", "2026-10-02T09:30:00Z", "confirmed")
    subscribers = [Subscriber("sms-1", "sms", True), Subscriber("email-1", "email", True)]
    count = fanout_appointment_notice(appointment, subscribers, InfraiClient())
    print(f"queued {count} patient-safe reminders")
