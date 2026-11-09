"""Add an optional compact skill index to the pinned Hermes installation."""
from pathlib import Path
import argparse

OLD = '    demoted = frozenset(cat for cat in skills_by_category if cat.split("/", 1)[0] in (compact_categories or frozenset()))\n'
NEW = ('    # Quatro: keep every skill name visible while reducing Discord prompt size.\n'
       '    demoted = (frozenset(skills_by_category) if os.environ.get("QUATRO_COMPACT_SKILLS") == "1"\n'
       '               else frozenset(cat for cat in skills_by_category if cat.split("/", 1)[0] in (compact_categories or frozenset())))\n')
OLD_NOTE = '        "\\n(Categories marked [names only] are outside the current coding "\n        "context, so their descriptions are omitted — the skills work "\n'
NEW_NOTE = '        "\\n(Categories marked [names only] omit descriptions to save context; "\n        "use skills_list to browse and the skills work "\n'


def apply(path):
    text = path.read_text(encoding='utf-8')
    if NEW in text and NEW_NOTE in text:
        return False
    if text.count(OLD) != 1 or text.count(OLD_NOTE) != 1:
        raise ValueError('The Hermes skill renderer changed. Review it before applying the patch.')
    text = text.replace(OLD, NEW).replace(OLD_NOTE, NEW_NOTE)
    compile(text, str(path), 'exec')
    path.write_text(text, encoding='utf-8')
    return True


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('file', type=Path)
    args = p.parse_args()
    print('Compact skill patch:', 'applied' if apply(args.file) else 'already applied')
