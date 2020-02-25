#! /usr/bin/env python3

"""
A script to quickly make/provision a fresh Miniconda installation from scratch.

This downloads a Miniconda binary e.g. from https://repo.continuum.io/miniconda/
like https://repo.continuum.io/miniconda/Miniconda3-latest-MacOSX-x86_64.sh for
MacOS or https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
for Windows, and unpacks and installs it locally.

This is tested on MacOS, Linux and Windows.

For additional information please read the README! ;)
"""

import argparse
import pathlib
import platform
import os
import re
import subprocess
import sys
from typing import Optional, List
from urllib import request


__version__ = '0.2.4'
__license__ = 'MIT'


# config data
config = dict(
    mc_base_url="https://repo.continuum.io/miniconda/",
    mc_name="Miniconda3",
    mc_version="latest",
    machine=platform.machine(),
    system=platform.system(),
    downloads_dir="~/Downloads",
    log_path="./mcinstall.log",
)

# derived config data
if config["system"] == "Darwin":
    config["system"] = "MacOSX"

known_systems = ["MacOSX", "Linux", "Windows"]

if config["system"] in known_systems:
    if config["system"] == "Windows":
        ext = "exe"
        config['machine'] = "x86_64"
    else:
        ext = "sh"

    if re.match("armv[67]l", config["machine"]):
        config["mc_base_url"] = (
            "https://github.com/jjhelmus/berryconda"
            "/releases/download/v2.0.0/"
        )
        config["mc_name"] = "Berryconda3"
        config["mc_version"] = "2.0.0"

    config["mc_blob_name"] = (
        f"{config['mc_name']}-{config['mc_version']}-"
        f"{config['system']}-{config['machine']}.{ext}"
    )


class MinicondaInstaller:
    """A tiny installer to bring you up to Python/Pip/Conda speed in seconds.

    This is mainly meant to install a fresh Miniconda distribution. It also
    allows to provision the installed base environment with additional packages
    via ``pip`` or ``conda``.

    N.B.:

    - Dependencies specified via ``conda`` environment files will not be
      available together with dependencies specified separately via ``pip``!
    """

    def __init__(self, dest_path: str, verbose: bool = False):
        self.dest_path = dest_path
        self.verbose = verbose
        self.installed_ok = False
        self.clean_dest_path = pathlib.Path(dest_path).expanduser().absolute()
        self.download_path = (
            pathlib.Path(config["downloads_dir"]).expanduser().absolute()
        )

    def __del__(self):
        if self.verbose and self.installed_ok:
            if config["system"] == "Windows":
                cmd = fr"{self.clean_dest_path}\condabin\activate"
            else:
                cmd = f"source {self.clean_dest_path}/bin/activate"
            print(f'Run this to start using your fresh Miniconda: "{cmd}".')

    def log(self, command: str):
        """Logger method to log results to ``log_path`` from ``config``.
        """
        log_path = pathlib.Path(config['log_path']).expanduser().absolute()
        with log_path.open("a") as f:
            f.write(f"{command}\n")

    def download(self, verbose: bool = False):
        """Download Miniconda locally at desired destination.
        """
        if not self.clean_dest_path.exists():
            if verbose:
                print(f"Making directory {self.clean_dest_path}.")
            self.clean_dest_path.mkdir(parents=True)

        if not self.download_path.exists():
            if verbose:
                print(f"Making directory {self.download_path}.")
            self.download_path.mkdir()

    def install_miniconda(self, verbose: bool = False):
        """Install Miniconda locally at desired destination.
        """
        mc_blob_path = self.download_path / config["mc_blob_name"]
        if not mc_blob_path.exists():
            url = f"{config['mc_base_url']}{config['mc_blob_name']}"
            if verbose:
                print(f"Downloading {url} ...")
            resp = request.urlopen(url)
            self.log(f'wget {url}')
            if resp.status >= 400:
                msg = f"Cannot download {url}. Verify URL components!"
                raise ValueError(msg)
            mc_blob = resp.read()
            if verbose:
                print(f"Copying to {mc_blob_path} ...")
            mc_blob_path.write_bytes(mc_blob)
            self.log(f"mv {config['mc_blob_name']} {mc_blob_path}")
        if not ((self.clean_dest_path / "bin" / "conda").exists() or \
                (self.clean_dest_path / "condabin" / "conda.bat").exists()):
            if config["system"] == "Windows":
                exec_cmd = (
                    f'start /wait "" {mc_blob_path} /InstallationType=JustMe '
                    f'/RegisterPython=0 /S /D={self.clean_dest_path}'
                )
                with open("temp.bat", "w") as fh:
                    fh.write(exec_cmd)
                p = subprocess.Popen("temp.bat", stdout=subprocess.PIPE)
                stdout, stderr = p.communicate()
                print(p.returncode)
                if p.returncode != 0:
                    self.log(str(stdout))
                    self.log(str(stderr))
                    raise ValueError("Installation failed...")
                else:
                    os.remove("temp.bat")
     
            else:
                exec_cmd = f"bash {mc_blob_path} -b -f -p {self.clean_dest_path}"
                if verbose:
                     print(f"Running command: {exec_cmd}")
                output = subprocess.check_output(exec_cmd.split())
                print(output.decode("utf8"))
            self.log(exec_cmd)

        if config["system"] == "Windows":
            source_cmd = fr"{self.clean_dest_path}\condabin\activate"
        else:
            source_cmd = f"source {self.clean_dest_path}/bin/activate"
        self.log(source_cmd)

        self.installed_ok = True
        
    def install_pip(
        self,
        dependencies: Optional[List[str]] = None,
        dependencies_path: Optional[str] = None,
        verbose: bool = False,
    ):
        """Pip-install dependencies.

        Dependencies can be specified in a list of package names or
        a dependencies file.
        """
        if dependencies:
            for dep in dependencies:
                # This will give output earlier when installed individually.
                if config["system"] == "Windows":
                    cmd = (
                        fr"{self.clean_dest_path}\condabin\activate && "
                        f"pip install {dep}"
                    )
                    output = subprocess.check_output(
                        cmd.split(), shell=True)
                else:
                    cmd = f"{self.clean_dest_path}/bin/pip install {dep}"
                    output = subprocess.check_output(cmd.split())
                if verbose:
                    print(f"Running command: {cmd}")
                self.log(cmd)
                print(output.decode("utf8"))

        if dependencies_path:
            if config["system"] == "Windows":
                cmd = (
                    fr"{self.clean_dest_path}\condabin\activate && "
                    f"pip install -r {dependencies_path}"
                )
                output = subprocess.check_output(cmd.split(), shell=True)
            else:
                cmd = (
                    f"{self.clean_dest_path}/bin/pip install "
                    f"-r {dependencies_path}"
                )
                output = subprocess.check_output(cmd.split())
            if verbose:
                print(f"Running command: {cmd}")
            self.log(cmd)
            print(output.decode("utf8"))

    def install_conda(
        self,
        channel: str = "conda-forge",
        dependencies: Optional[List[str]] = None,
        dependencies_path: Optional[str] = None,
        environment_path: Optional[str] = None,
        verbose: bool = False,
    ):
        """Conda-install dependencies.

        Dependencies can be specified in a list of package names or
        a dependencies file or a conda environment file (which will
        create a new environment).
        """
        if dependencies:
            for dep in dependencies:
                # This will give output earlier when installed individually.
                if config["system"] == "Windows":
                    cmd = (
                        fr"{self.clean_dest_path}\condabin\conda install "
                        f"-y {dep}"
                    )
                    output = subprocess.check_output(cmd.split(), shell=True)
                else:
                    cmd = (
                        f"{self.clean_dest_path}/bin/conda install -y "
                        f"-c {channel} {dep}"
                    )
                    output = subprocess.check_output(cmd.split())
                if verbose:
                    print(f"Running command: {cmd}")
                self.log(cmd)
                print(output.decode("utf8"))

        if dependencies_path:
            if config["system"] == "Windows":
                cmd = (
                    fr"{self.clean_dest_path}\condabin\conda install -y "
                    f"--file {dependencies_path}"
                )
                output = subprocess.check_output(cmd.split(), shell=True)
            else:
                cmd = (
                    f"{self.clean_dest_path}/bin/conda install -y "
                    f"--file {dependencies_path}"
                )
                output = subprocess.check_output(cmd.split())
            if verbose:
                print(f"Running command: {cmd}")
            self.log(cmd)
            print(output.decode("utf8"))

        if environment_path:
            if config["system"] == "Windows":
                cmd = (
                   fr"{self.clean_dest_path}\condabin\conda env create "
                   f"--file {environment_path}"
                )
                output = subprocess.check_output(cmd.split(), shell=True)
            else:
                cmd = (
                   f"{self.clean_dest_path}/bin/conda env create "
                   f"--file {environment_path}"
                )
                output = subprocess.check_output(cmd.split())
            if verbose:
                print(f"Running command: {cmd}")
            self.log(cmd)
            print(output.decode("utf8"))


def main():
    """Main function called when used on the command-line.
    """
    systems = ", ".join(known_systems)
    desc = (
        f'Quick-install a fresh Miniconda from {config["mc_base_url"]} '
        f'for {systems}.'
    )
    p = argparse.ArgumentParser(description=desc)

    p.add_argument(
        "path",
        metavar="DEST_DIR",
        help="The destination directory (will be created if needed).",
    )
    p.add_argument(
        "--verbose", action="store_true", help="Output additional information."
    )
    p.add_argument(
        "--pip-dependencies",
        metavar="LIST",
        default="",
        help="Comma-separated list of pip requirements.",
    )
    p.add_argument(
        "--pip-dependencies-path",
        metavar="PATH",
        help="Path of a pip requirements file, usually named requirements.txt.",
    )
    p.add_argument(
        "--conda-dependencies",
        metavar="LIST",
        default="",
        help="Comma-separated list of conda requirements.",
    )
    p.add_argument(
        "--conda-dependencies-path",
        metavar="PATH",
        help=(
            "Path of a conda dependencies file, usually named requirements.txt. "
            "(This is not for creating a conda environment "
            "with something like environment.yml!)"
        ),
    )
    p.add_argument(
        "--conda-environment-path",
        metavar="PATH",
        help="Path of a conda environment file, usually named environment.yml.",
    )

    if config["system"] not in known_systems:
        msg = (
            f"""Don't know how to handle operating system '{config["system"]}'. """
            "Want to provide a patch?"
        )
        print(msg)
        sys.exit(0)

    args = p.parse_args()

    if args.path:
        inst = MinicondaInstaller(dest_path=args.path, verbose=args.verbose)
        inst.download(verbose=args.verbose)
        inst.install_miniconda(verbose=args.verbose)
        if args.pip_dependencies or args.pip_dependencies_path:
            inst.install_pip(
                dependencies=args.pip_dependencies.split(",") if args.pip_dependencies else None,
                dependencies_path=args.pip_dependencies_path,
                verbose=args.verbose,
            )
        if (
            args.conda_dependencies
            or args.conda_dependencies_path
            or args.conda_environment_path
        ):
            inst.install_conda(
                dependencies=args.conda_dependencies.split(",") if args.conda_dependencies else None,
                dependencies_path=args.conda_dependencies_path,
                environment_path=args.conda_environment_path,
                verbose=args.verbose,
            )


if __name__ == "__main__":
    main()
