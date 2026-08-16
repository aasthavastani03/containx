# ContainX

A lightweight Linux container runtime built from scratch in Python.

ContainX demonstrates Linux container isolation using namespaces, chroot, /proc, and process management without relying on Docker.

## Features

- PID namespace isolation
- UTS namespace isolation
- Mount namespace isolation
- Filesystem isolation using chroot
- /proc filesystem support
- Container process tracking
- Container lifecycle management
- Container logs
- Container inspection
- Execute commands inside running containers
- Start and stop containers
- Remove containers
- CLI interface

## Architecture

ContainX uses Linux kernel features to create isolated processes:

```text
ContainX CLI
     |
     v
Python Runtime
     |
     +---- unshare
     |      |
     |      +---- PID namespace
     |      +---- UTS namespace
     |      +---- Mount namespace
     |
     +---- chroot
     |      |
     |      +---- Container root filesystem
     |
     +---- /proc
     |
     +---- Process management
```

## Commands

### Run a container

```bash
python3 containx.py run echo "hello from containx"
```

### List containers

```bash
python3 containx.py ps
```

### View logs

```bash
python3 containx.py logs CONTAINER_ID
```

### Inspect a container

```bash
python3 containx.py inspect CONTAINER_ID
```

### Execute a command inside a running container

```bash
python3 containx.py exec CONTAINER_ID hostname
```

### Stop a container

```bash
python3 containx.py stop CONTAINER_ID
```

### Remove a container

```bash
python3 containx.py rm CONTAINER_ID
```

## Example

```text
$ python3 containx.py run sleep 300
Container ID: 3a4fd6326b72
Container PID: 7036

$ python3 containx.py exec 3a4fd6326b72 hostname
containx
Command exited with code: 0

$ python3 containx.py exec 3a4fd6326b72 ps
    PID TTY          TIME CMD
      5 ?        00:00:00 ps
Command exited with code: 0
```

## Requirements

- Linux or WSL2
- Python 3
- sudo privileges
- Linux root filesystem

Developed and tested using Ubuntu on WSL2.

## Project Structure

```text
containx/
├── containx.py
├── rootfs/
├── state/
└── README.md
```

## Concepts Demonstrated

- Linux namespaces
- PID isolation
- UTS isolation
- Mount namespaces
- Filesystem isolation
- chroot
- /proc
- Linux process trees
- Signals and process termination
- Python subprocess management
- CLI design

## Limitations

ContainX is an educational container runtime and is not intended to provide the security, networking, resource isolation, or production features of Docker.

## Future Improvements

- Network namespaces
- CPU and memory limits using cgroups
- Container networking
- Volume mounts
- Better error handling
- Container restart support
- Image management
- Automated tests

## License

This project is intended for educational and experimentation purposes.