from argparse import ArgumentParser

from .logo import logo2 as logo

def main():
    print(logo)

    parser = ArgumentParser(description='Pixee CLI')
    subparsers = parser.add_subparsers(dest="command", help='Commands')

    fix = subparsers.add_parser('fix', help='Find and fix vulnerabilities')
    fix.add_argument('path', nargs='?', help='Path to the project to fix')

    subparsers.add_parser('triage', help='Triage findings')
    subparsers.add_parser('remediate', help='Fix vulnerabilities from external tools')


    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "fix" and not args.path:
        return

if __name__ == '__main__':
    main()
