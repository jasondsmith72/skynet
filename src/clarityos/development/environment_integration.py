"""
Development Environment Integration for ClarityOS

This module provides capabilities for ClarityOS to interact with development tools
and environments, particularly version control systems like Git. This is a key
component for self-programming capabilities, allowing ClarityOS to manage its own
source code and development lifecycle.
"""

import os
import subprocess
import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Union

logger = logging.getLogger(__name__)

class GitInterface:
    """
    Interface for interacting with Git repositories.
    
    Provides a programmatic interface to Git operations such as commit, push,
    pull, and branch management, enabling ClarityOS to manage its own codebase.
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize the Git interface.
        
        Args:
            repo_path: Optional path to the Git repository. If not provided,
                       the current directory is used.
        """
        self.repo_path = repo_path or os.getcwd()
        self._validate_repo()
    
    def _validate_repo(self) -> bool:
        """
        Validate that the specified path is a Git repository.
        
        Returns:
            True if the path is a valid Git repository, False otherwise.
        """
        try:
            result = self._run_git_command("rev-parse", "--is-inside-work-tree")
            if result.strip() != "true":
                raise ValueError(f"Not a Git repository: {self.repo_path}")
            return True
        except subprocess.CalledProcessError:
            raise ValueError(f"Not a Git repository: {self.repo_path}")
    
    def _run_git_command(self, *args) -> str:
        """
        Run a Git command and return the output.
        
        Args:
            *args: The Git command and arguments to run.
            
        Returns:
            The command output as a string.
        """
        cmd = ["git"] + list(args)
        logger.debug(f"Running Git command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            raise
    
    def status(self) -> Dict[str, Any]:
        """
        Get the current status of the repository.
        
        Returns:
            A dictionary containing the repository status.
        """
        status_output = self._run_git_command("status", "--porcelain")
        branch_output = self._run_git_command("rev-parse", "--abbrev-ref", "HEAD")
        
        files = {
            "modified": [],
            "added": [],
            "deleted": [],
            "untracked": []
        }
        
        for line in status_output.splitlines():
            if not line.strip():
                continue
                
            status = line[:2]
            filename = line[3:].strip()
            
            if status == "M ":
                files["modified"].append(filename)
            elif status == "A ":
                files["added"].append(filename)
            elif status == "D ":
                files["deleted"].append(filename)
            elif status == "??":
                files["untracked"].append(filename)
        
        return {
            "branch": branch_output.strip(),
            "files": files,
            "has_changes": bool(status_output.strip())
        }
    
    def commit(self, message: str, files: Optional[List[str]] = None) -> str:
        """
        Commit changes to the repository.
        
        Args:
            message: The commit message.
            files: Optional list of files to commit. If not provided, all
                  changed files are committed.
        
        Returns:
            The commit hash.
        """
        if files:
            # Add specific files
            for file in files:
                self._run_git_command("add", file)
        else:
            # Add all changed files
            self._run_git_command("add", ".")
        
        # Commit the changes
        self._run_git_command("commit", "-m", message)
        
        # Get the commit hash
        commit_hash = self._run_git_command("rev-parse", "HEAD").strip()
        
        return commit_hash
    
    def push(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Push changes to a remote repository.
        
        Args:
            remote: The remote repository name.
            branch: Optional branch name. If not provided, the current branch is used.
            
        Returns:
            True if the push was successful, False otherwise.
        """
        current_branch = branch or self._run_git_command(
            "rev-parse", "--abbrev-ref", "HEAD"
        ).strip()
        
        try:
            self._run_git_command("push", remote, current_branch)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def pull(self, remote: str = "origin", branch: Optional[str] = None) -> bool:
        """
        Pull changes from a remote repository.
        
        Args:
            remote: The remote repository name.
            branch: Optional branch name. If not provided, the current branch is used.
            
        Returns:
            True if the pull was successful, False otherwise.
        """
        current_branch = branch or self._run_git_command(
            "rev-parse", "--abbrev-ref", "HEAD"
        ).strip()
        
        try:
            self._run_git_command("pull", remote, current_branch)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def checkout(self, branch: str, create: bool = False) -> bool:
        """
        Checkout a branch.
        
        Args:
            branch: The branch name.
            create: If True, create the branch if it doesn't exist.
            
        Returns:
            True if the checkout was successful, False otherwise.
        """
        try:
            if create:
                self._run_git_command("checkout", "-b", branch)
            else:
                self._run_git_command("checkout", branch)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def get_diff(self, file: Optional[str] = None) -> str:
        """
        Get the diff of the current changes.
        
        Args:
            file: Optional file to get the diff for. If not provided, the diff
                 for all changed files is returned.
            
        Returns:
            The diff as a string.
        """
        if file:
            return self._run_git_command("diff", file)
        else:
            return self._run_git_command("diff")
    
    def get_log(self, count: int = 10) -> List[Dict[str, str]]:
        """
        Get the commit history.
        
        Args:
            count: The number of commits to retrieve.
            
        Returns:
            A list of dictionaries containing commit information.
        """
        log_format = {
            "hash": "%H",
            "author": "%an",
            "email": "%ae",
            "date": "%ai",
            "message": "%s"
        }
        
        format_str = "--pretty=format:" + json.dumps(log_format).replace('"', '\\"')
        log_output = self._run_git_command("log", f"-{count}", format_str)
        
        entries = []
        for line in log_output.splitlines():
            if line.strip():
                entries.append(json.loads(line))
        
        return entries


class BuildSystem:
    """
    Interface for interacting with build systems.
    
    Provides capabilities for ClarityOS to build and test code, enabling
    self-programming with proper verification.
    """
    
    def __init__(self, project_path: Optional[str] = None):
        """
        Initialize the build system interface.
        
        Args:
            project_path: Optional path to the project. If not provided,
                          the current directory is used.
        """
        self.project_path = project_path or os.getcwd()
    
    def _run_command(self, *args) -> Tuple[bool, str]:
        """
        Run a command and return the result.
        
        Args:
            *args: The command and arguments to run.
            
        Returns:
            A tuple of (success, output).
        """
        cmd = list(args)
        logger.debug(f"Running command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                check=True,
                capture_output=True,
                text=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {e.stderr}")
            return False, e.stderr
    
    def run_tests(self, test_path: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Run tests for the project.
        
        Args:
            test_path: Optional path to specific tests. If not provided,
                       all tests are run.
            
        Returns:
            A tuple of (success, results).
        """
        cmd = ["python", "-m", "unittest"]
        if test_path:
            cmd.append(test_path)
        
        success, output = self._run_command(*cmd)
        
        # Parse the test results
        results = {
            "success": success,
            "output": output,
            "passed": output.count(" ... ok"),
            "failed": output.count(" ... FAIL"),
            "errors": output.count(" ... ERROR")
        }
        
        return success, results
    
    def run_linter(self, path: Optional[str] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Run a linter on the project code.
        
        Args:
            path: Optional path to lint. If not provided, the entire project is linted.
            
        Returns:
            A tuple of (success, results).
        """
        cmd = ["flake8"]
        if path:
            cmd.append(path)
        
        success, output = self._run_command(*cmd)
        
        # Parse the linter results
        error_count = len(output.splitlines()) if output else 0
        results = {
            "success": success,
            "output": output,
            "error_count": error_count
        }
        
        return success, results


class EnvironmentIntegrationSystem:
    """
    Main system for development environment integration in ClarityOS.
    
    This system provides tools for interacting with development environments,
    version control systems, and build tools, enabling self-programming capabilities.
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize the Environment Integration System.
        
        Args:
            repo_path: Optional path to the repository. If not provided,
                       the current directory is used.
        """
        self.repo_path = repo_path or os.getcwd()
        self.git = GitInterface(self.repo_path)
        self.build = BuildSystem(self.repo_path)
    
    def implement_and_commit(self, file_path: str, content: str, 
                            commit_message: str, run_tests: bool = True,
                            push: bool = False) -> Dict[str, Any]:
        """
        Implement a change, test it, and commit it to the repository.
        
        This is a high-level method that encapsulates the entire workflow
        of implementing a change, including:
        1. Writing the file
        2. Running tests and static analysis
        3. Committing the change
        4. Optionally pushing the change
        
        Args:
            file_path: The path to the file to implement/modify
            content: The content to write to the file
            commit_message: The commit message
            run_tests: Whether to run tests before committing
            push: Whether to push the changes after committing
            
        Returns:
            A dictionary with the result of the operation
        """
        results = {
            "success": False,
            "steps": {}
        }
        
        # Step 1: Write the file
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(os.path.join(self.repo_path, file_path))
            os.makedirs(dir_path, exist_ok=True)
            
            # Write the file
            with open(os.path.join(self.repo_path, file_path), 'w') as f:
                f.write(content)
            
            results["steps"]["write_file"] = {
                "success": True,
                "message": f"File written: {file_path}"
            }
        except Exception as e:
            results["steps"]["write_file"] = {
                "success": False,
                "error": str(e)
            }
            return results
        
        # Step 2: Run tests if requested
        if run_tests:
            test_success, test_results = self.build.run_tests()
            results["steps"]["run_tests"] = {
                "success": test_success,
                "results": test_results
            }
            
            if not test_success:
                return results
        
        # Step 3: Commit the change
        try:
            commit_hash = self.git.commit(commit_message, [file_path])
            results["steps"]["commit"] = {
                "success": True,
                "commit_hash": commit_hash,
                "message": f"Changes committed: {commit_message}"
            }
        except Exception as e:
            results["steps"]["commit"] = {
                "success": False,
                "error": str(e)
            }
            return results
        
        # Step 4: Push if requested
        if push:
            try:
                push_success = self.git.push()
                results["steps"]["push"] = {
                    "success": push_success,
                    "message": "Changes pushed to remote" if push_success else "Failed to push changes"
                }
            except Exception as e:
                results["steps"]["push"] = {
                    "success": False,
                    "error": str(e)
                }
                return results
        
        # All steps completed successfully
        results["success"] = True
        return results
