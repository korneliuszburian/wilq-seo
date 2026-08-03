import threading
import time

from wilq.content.drafts import draft_assurance_runtime


def test_assurance_executor_keeps_parallel_slots_for_independent_checks() -> None:
    barrier = threading.Barrier(2)

    def check() -> None:
        barrier.wait(timeout=1)
        time.sleep(0.01)

    futures = [draft_assurance_runtime._ASSURANCE_EXECUTOR.submit(check) for _ in range(2)]
    for future in futures:
        future.result(timeout=2)
