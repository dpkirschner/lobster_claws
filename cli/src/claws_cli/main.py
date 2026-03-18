"""Meta-CLI entry point with entry_points discovery and routing."""

import sys
from importlib.metadata import entry_points


def discover_skills():
    """Discover installed skills via Python entry points.

    Returns a dict mapping skill name to EntryPoint for the 'claws.skills' group.
    """
    eps = entry_points(group="claws.skills")
    return {ep.name: ep for ep in eps}


def main():
    """Entry point for the claws meta-CLI.

    With no arguments: list available skills.
    With a skill name: load and delegate to that skill.
    With an unknown name: print error to stderr and exit 2.
    """
    skills = discover_skills()

    if len(sys.argv) < 2:
        if not skills:
            print("No skills found. Install a claws skill package to get started.")
        else:
            print("Available claws:")
            for name in sorted(skills):
                print(f"  {name}")
            print()
            print("Usage: claws <skill> [args...]")
        return

    skill_name = sys.argv[1]

    if skill_name not in skills:
        available = ", ".join(sorted(skills)) if skills else "none"
        print(f"Unknown skill: {skill_name}. Available: {available}", file=sys.stderr)
        sys.exit(2)

    ep = skills[skill_name]
    fn = ep.load()
    sys.argv = [skill_name] + sys.argv[2:]
    fn()
