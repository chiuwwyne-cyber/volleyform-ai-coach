import os

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

FORBIDDEN_TOKENS = (
    "cv2.imshow",
    "cv2.namedWindow",
    "cv2.waitKey",
    "tkinter",
    "PyQt",
)


def main():
    offenders = []
    for dirpath, _dirnames, filenames in os.walk(BACKEND_DIR):
        if "__pycache__" in dirpath:
            continue
        for filename in filenames:
            if filename == os.path.basename(__file__):
                continue
            if not filename.endswith(".py"):
                continue
            path = os.path.join(dirpath, filename)
            with open(path, "r", encoding="utf-8") as file:
                source = file.read()
            for token in FORBIDDEN_TOKENS:
                if token in source:
                    offenders.append(f"{os.path.relpath(path, ROOT_DIR)}: {token}")

    if offenders:
        raise SystemExit("Backend UI code is not allowed:\n" + "\n".join(offenders))

    print("backend no-ui ok")
    print(f"forbidden tokens: {len(FORBIDDEN_TOKENS)}")


if __name__ == "__main__":
    main()
