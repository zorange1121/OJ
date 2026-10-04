
from services.judge import run_judge
from services.queue import consume


def main() -> None:
    consume(run_judge)


if __name__ == "__main__":
    main()
