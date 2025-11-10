# Listing Docker Containers

This section explains how to view all running (or stopped) containers managed by the DevOps Orchestrator CLI.

## Command

To list all containers, use the CLI command:

```bash
python cli.py containers
```

By default, this will only show **running containers**.  

To include stopped containers, use the `--all` or `-a` flag:

```bash
python cli.py containers --all
```

## Output

The command displays a **table** of containers with the following information:

| Container Name | Image         | Status      | Ports           |
|----------------|---------------|------------|----------------|
| mysql          | mysql:8.0     | running    | 3306->3306     |
| vault          | vault:latest  | running    | 8200->8200     |
| phpmyadmin     | phpmyadmin    | exited     | 8080->80       |

> The table is rendered using `rich` for a clean, colorized display in the terminal.

## Notes

- Make sure Colima is running. The CLI will attempt to start it automatically if not.  
- The `Ports` column maps **host port → container port**.  
- Only containers created by the orchestrator are listed.  

## Example

```bash
$ python cli.py containers
```

![Example Output](assets/containers_example.png)

