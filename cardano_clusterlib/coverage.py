from typing import List


def record_cli_coverage(cli_args: List[str], coverage_dict: dict) -> None:
    """Record coverage info for CLI commands.

    Args:
        cli_args: A list of command and it's arguments.
        coverage_dict: A dictionary with coverage info.
    """
    parent_dict = coverage_dict
    prev_arg = ""
    for arg in cli_args:
        # if the current argument is a parameter to an option, skip it
        if prev_arg.startswith("--") and not arg.startswith("--"):
            continue
        prev_arg = arg

        cur_dict = parent_dict.get(arg)
        # initialize record if it doesn't exist yet
        if not cur_dict:
            parent_dict[arg] = {"_count": 0}
            cur_dict = parent_dict[arg]

        # increment count
        cur_dict["_count"] += 1

        # set new parent dict
        if not arg.startswith("--"):
            parent_dict = cur_dict
