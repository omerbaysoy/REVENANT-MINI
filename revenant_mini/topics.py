PREFIX = "revenant-mini/v1"


def worker_topic(worker_id: str, name: str) -> str:
    return f"{PREFIX}/workers/{worker_id}/{name}"


def hello(worker_id: str) -> str:
    return worker_topic(worker_id, "hello")


def telemetry(worker_id: str) -> str:
    return worker_topic(worker_id, "telemetry")


def status(worker_id: str) -> str:
    return worker_topic(worker_id, "status")


def heartbeat(worker_id: str) -> str:
    return worker_topic(worker_id, "heartbeat")


def result(worker_id: str) -> str:
    return worker_topic(worker_id, "result")


def commands_all() -> str:
    return f"{PREFIX}/commands/all"


def command(worker_id: str) -> str:
    return f"{PREFIX}/commands/{worker_id}"


def workers_wildcard() -> str:
    return f"{PREFIX}/workers/+/+"
