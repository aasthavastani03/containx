import uuid
import argparse
import subprocess
import json
import os
import time

STATE_DIR = "state"
DEFAULT_ROOTFS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rootfs")

CGROUP_ROOT = "/sys/fs/cgroup"
CGROUP_NAME = "containx"


def setup_cgroup(pid):
    cgroup_path = os.path.join(CGROUP_ROOT, CGROUP_NAME)

    subprocess.run(
        ["sudo", "mkdir", "-p", cgroup_path],
        check=True
    )

    subprocess.run(
        ["sudo", "sh", "-c",
         f"echo {pid} > {cgroup_path}/cgroup.procs"],
        check=True
    )

    subprocess.run(
        ["sudo", "sh", "-c",
         f'echo "50000 100000" > {cgroup_path}/cpu.max'],
        check=True
    )


def find_container_pid(host_pid):
    """
    Find the host PID of PID 1 inside the container's PID namespace.
    """
    for _ in range(100):
        try:
            # Start with the process created by Popen and walk
            # through all of its descendants.
            queue = [host_pid]
            visited = set()

            while queue:
                pid = queue.pop(0)

                if pid in visited:
                    continue

                visited.add(pid)

                try:
                    with open(f"/proc/{pid}/status") as f:
                        status = f.read()

                    for line in status.splitlines():
                        if line.startswith("NSpid:"):
                            nspids = line.split()

                            # Last number is the PID inside the
                            # process's own namespace.
                            if nspids[-1] == "1":
                                return pid

                    with open(f"/proc/{pid}/task/{pid}/children") as f:
                        children = f.read().split()

                    for child in children:
                        queue.append(int(child))

                except (FileNotFoundError, ProcessLookupError, PermissionError):
                    continue

        except (FileNotFoundError, ProcessLookupError):
            pass

        time.sleep(0.05)

    return host_pid


def main():
    parser = argparse.ArgumentParser(
        prog="containx",
        description="A Linux container runtime built from scratch"
    )

    subparsers = parser.add_subparsers(dest="subcommand")

    # ---------------- RUN ----------------

    run_parser = subparsers.add_parser(
        "run",
        help="Run a command in a container"
    )

    run_parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run"
    )

    run_parser.add_argument(
        "--rootfs",
        default=DEFAULT_ROOTFS,
        help="Path to the container root filesystem"
    )

    # ---------------- PS ----------------

    subparsers.add_parser(
        "ps",
        help="List containers"
    )

    # ---------------- LOGS ----------------

    logs_parser = subparsers.add_parser(
        "logs",
        help="Show container logs"
    )

    logs_parser.add_argument(
        "container_id",
        help="Container ID"
    )

    # ---------------- INSPECT ----------------

    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Show container details"
    )

    inspect_parser.add_argument(
        "container_id",
        help="Container ID"
    )

    # ---------------- EXEC ----------------

    exec_parser = subparsers.add_parser(
        "exec",
        help="Run a command inside a running container"
    )

    exec_parser.add_argument(
        "container_id",
        help="Container ID"
    )

    exec_parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run"
    )

    # ---------------- STOP ----------------

    stop_parser = subparsers.add_parser(
        "stop",
        help="Stop a running container"
    )

    stop_parser.add_argument(
        "container_id",
        help="Container ID"
    )

    # ---------------- RM ----------------

    rm_parser = subparsers.add_parser(
        "rm",
        help="Remove a container"
    )

    rm_parser.add_argument(
        "container_id",
        help="Container ID"
    )

    args = parser.parse_args()

    # Make sure state directory exists
    os.makedirs(STATE_DIR, exist_ok=True)

    # ============================================================
    # PS
    # ============================================================

    if args.subcommand == "ps":
        print("CONTAINERS")

        for filename in os.listdir(STATE_DIR):
            if filename.endswith(".json"):

                with open(
                    os.path.join(STATE_DIR, filename)
                ) as f:
                    container = json.load(f)

                pid = container["pid"]

                if container["status"] == "running":
                    if pid and os.path.exists(f"/proc/{pid}"):
                        status = "running"
                    else:
                        status = "exited"
                else:
                    status = container["status"]

                print(
                    container["id"],
                    container["pid"],
                    status,
                    " ".join(container["command"])
                )

    # ============================================================
    # LOGS
    # ============================================================

    elif args.subcommand == "logs":

        filename = os.path.join(
            STATE_DIR,
            f"{args.container_id}.log"
        )

        if not os.path.exists(filename):
            print("Logs not found")
            return

        with open(filename) as f:
            print(f.read(), end="")

    # ============================================================
    # INSPECT
    # ============================================================

    elif args.subcommand == "inspect":

        filename = os.path.join(
            STATE_DIR,
            f"{args.container_id}.json"
        )

        if not os.path.exists(filename):
            print("Container not found")
            return

        with open(filename) as f:
            container = json.load(f)

        print(
            json.dumps(
                container,
                indent=2
            )
        )

    # ============================================================
    # EXEC
    # ============================================================

    elif args.subcommand == "exec":

        filename = os.path.join(
            STATE_DIR,
            f"{args.container_id}.json"
        )

        if not os.path.exists(filename):
            print("Container not found")
            return

        with open(filename) as f:
            container = json.load(f)

        if container["status"] != "running":
            print("Container is not running")
            return

        if not args.command:
            print("No command specified")
            return

        result = subprocess.run(
    [
        "sudo",
        "nsenter",
        "--target",
        str(container["pid"]),
        "--pid",
        "--uts",
        "--mount",
        "--",
        "chroot",
        DEFAULT_ROOTFS,
        "/bin/sh",
        "-c",
        'exec "$@"',
        "sh",
    ] + args.command
)

        print(
            f"Command exited with code: {result.returncode}"
        )

    # ============================================================
    # STOP
    # ============================================================

    elif args.subcommand == "stop":

        filename = os.path.join(
            STATE_DIR,
            f"{args.container_id}.json"
        )

        if not os.path.exists(filename):
            print("Container not found")
            return

        with open(filename) as f:
            container = json.load(f)

        if container["status"] != "running":
            print("Container is not running")
            return

        try:
            subprocess.run(
                ["sudo", "kill", "-15", str(container["pid"])]
            )
        except ProcessLookupError:
            pass

        container["status"] = "stopped"

        with open(filename, "w") as f:
            json.dump(
                container,
                f,
                indent=2
            )

        print(
            f"Container {args.container_id} stopped"
        )

    # ============================================================
    # RM
    # ============================================================

    elif args.subcommand == "rm":

        filename = os.path.join(
            STATE_DIR,
            f"{args.container_id}.json"
        )

        if not os.path.exists(filename):
            print("Container not found")
            return

        with open(filename) as f:
            container = json.load(f)

        if container["status"] == "running":
            print("Cannot remove a running container")
            return

        os.remove(filename)

        log_filename = os.path.join(
            STATE_DIR,
            f"{args.container_id}.log"
        )

        if os.path.exists(log_filename):
            os.remove(log_filename)

        print(
            f"Container {args.container_id} removed"
        )

    # ============================================================
    # RUN
    # ============================================================

    elif args.subcommand == "run":

        if not args.command:
            print("No command specified")
            return

        container_id = uuid.uuid4().hex[:12]

        container_info = {
            "id": container_id,
            "pid": None,
            "command": args.command,
            "status": "created"
        }

        state_file = os.path.join(
            STATE_DIR,
            f"{container_id}.json"
        )

        log_filename = os.path.join(
            STATE_DIR,
            f"{container_id}.log"
        )

        # Save initial state
        with open(state_file, "w") as f:
            json.dump(
                container_info,
                f,
                indent=2
            )

        print(
            f"Container ID: {container_id}"
        )

        log_file = open(
            log_filename,
            "w"
        )

        # Start container
        os.makedirs(os.path.join(args.rootfs, "proc"), exist_ok=True)
        process = subprocess.Popen(
            [
                "sudo",
                "unshare",
                "--pid",
                "--fork",
                "--uts",
                "--mount",
                "--net",
                "chroot",
                args.rootfs,
                "/bin/sh",
                "-c",
                'mount -t proc proc /proc && '
                'hostname containx && '
                'exec "$@"',
                "sh"
            ] + args.command,
            stdout=log_file,
            stderr=subprocess.STDOUT
        )

        # Find the real PID 1 inside the container
        real_pid = find_container_pid(
            process.pid
        )

        container_info["pid"] = real_pid
        container_info["status"] = "running"

        # Save running state
        with open(state_file, "w") as f:
            json.dump(
                container_info,
                f,
                indent=2
            )

        print(
            f"Container PID: {real_pid}"
        )

        # Wait for container to finish
        exit_code = process.wait()

        log_file.close()

        container_info["status"] = "exited"
        container_info["exit_code"] = exit_code

        # Save final state
        with open(state_file, "w") as f:
            json.dump(
                container_info,
                f,
                indent=2
            )

        print(
            f"Container exited with code: {exit_code}"
        )

    # ============================================================
    # NO COMMAND
    # ============================================================

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
