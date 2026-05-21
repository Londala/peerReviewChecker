import sys
import argparse
from dotenv import load_dotenv
from checker.input import normalize, ValidationError
from checker.pipeline import check
from checker.display import format_human, format_json
from batch import parse_file, stream_check

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Check if a journal article is peer-reviewed.")
    parser.add_argument("--title")
    parser.add_argument("--doi")
    parser.add_argument("--issn")
    parser.add_argument("--author")
    parser.add_argument("--journal")
    parser.add_argument("--file", help="CSV or JSON file of articles")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    args = parser.parse_args()

    if args.file:
        _run_batch(args.file, args.json_output)
    elif any([args.title, args.doi, args.issn, args.author, args.journal]):
        _run_single(args, args.json_output)
    else:
        _run_interactive(args.json_output)


def _run_single(args, json_output: bool):
    try:
        article = normalize(
            title=args.title, doi=args.doi, issn=args.issn,
            author=args.author, journal=args.journal,
        )
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    verdict = check(article)
    print(format_json(verdict) if json_output else format_human(verdict))


def _run_interactive(json_output: bool):
    print("Enter article details (press Enter to skip optional fields):")
    title = input("Title: ").strip() or None
    doi = input("DOI: ").strip() or None
    issn = input("ISSN (optional): ").strip() or None
    try:
        article = normalize(title=title, doi=doi, issn=issn)
    except ValidationError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    verdict = check(article)
    print(format_json(verdict) if json_output else format_human(verdict))


def _run_batch(file_path: str, json_output: bool):
    try:
        articles = list(parse_file(file_path))
    except (ValueError, FileNotFoundError) as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        sys.exit(1)

    error_count = 0
    for article, verdict, error in stream_check(articles):
        label = article.doi or article.title or "unknown"
        if error:
            print(f"ERROR [{label}]: {error}", file=sys.stderr)
            error_count += 1
        else:
            if json_output:
                print(format_json(verdict))
            else:
                print(format_human(verdict, article_label=label))

    if error_count:
        print(f"\n{error_count} article(s) failed to process.", file=sys.stderr)


if __name__ == "__main__":
    main()
