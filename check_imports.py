import subprocess
import sys
import os

def get_python_files():
    result = subprocess.run(['find', 'src', '-name', '*.py'], capture_output=True, text=True)
    if result.returncode != 0:
        print("Error finding python files:")
        print(result.stderr)
        sys.exit(1)
    return result.stdout.strip().split('\n')

def main():
    python_files = get_python_files()
    failed_imports = []

    for filepath in python_files:
        # Convert file path to module path
        module_path = filepath.replace('/', '.').replace('.py', '')

        try:
            print(f"Trying to import {module_path}...")
            # Use subprocess to isolate the import
            env = os.environ.copy()
            env['PYTHONPATH'] = 'src'
            result = subprocess.run(
                [sys.executable, '-c', f'import {module_path}'],
                capture_output=True,
                text=True,
                env=env,
                timeout=30
            )
            if result.returncode != 0:
                print(f"Failed to import {module_path}:")
                print("--- STDOUT ---")
                print(result.stdout)
                print("--- STDERR ---")
                print(result.stderr)
                failed_imports.append(module_path)
        except Exception as e:
            print(f"An unexpected error occurred while trying to import {module_path}: {e}")
            failed_imports.append(module_path)

    if failed_imports:
        print("\n--- Failed Imports ---")
        for module in failed_imports:
            print(module)
        sys.exit(1)
    else:
        print("\nAll python files imported successfully!")

if __name__ == "__main__":
    main()
