"""
SasView command line interface.

sasview [options] -m module [args...]
    Run module as main.
sasview [options] -c "python statements" [args...]
    Execute python statements with sasview libraries available.
sasview [options] script [args...]
    Run script with sasview libraries available
sasview [options]
    Start sasview gui if not interactive

Options:

    -i: Start an interactive interpreter after the command is executed.
    -q: Don't print.
    -V: Print SasView version.
"""
import sys

# TODO: Support dropping datafiles onto .exe?
# TODO: Maybe use the bumps cli with project file as model?

import argparse

def parse_cli(argv):
    """
    Parse the command argv returning an argparse.Namespace.

    * version: bool - print version
    * command: str - string to exec
    * module: str - module to run as main
    * interactive: bool - run interactive
    * args: list[str] - additional arguments, or script + args
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-V", "--version", action='store_true',
        help="Print sasview version and exit")
    parser.add_argument("-m", "--module", type=str,
        help="Run module with remaining arguments sent to main")
    parser.add_argument("-c", "--command", type=str,
        help="Execute command")
    parser.add_argument("-i", "--interactive", action='store_true',
        help="Start interactive interpreter after running command")
    parser.add_argument("-q", "--quiet", action='store_true',
        help="Don't print banner when entering interactive mode")
    parser.add_argument("args", nargs="*",
        help="script followed by args")

    # Special case: abort argument processing after -i, -m or -c.
    have_trigger = False
    collect_rest = False
    keep = []
    rest = []
    for arg in argv[1:]:
        # Append argument to the parser argv or collect them as extra args.
        if collect_rest:
            rest.append(arg)
        else:
            keep.append(arg)
        # For an action that needs an argument (e.g., -m module) we need
        # to keep the next argument for the parser, but the remaining arguments
        # get collected as extra args. Trigger and collect will happen in one
        # step if the trigger requires no args or if the arg was provided
        # with the trigger (e.g., -mmodule)
        if have_trigger:
            collect_rest = True
        if arg.startswith('-m') or arg.startswith('--module'):
            have_trigger = True
            collect_rest = arg not in ('-m', '--module')
        elif arg.startswith('-c') or arg.startswith('--command'):
            have_trigger = True
            collect_rest = arg not in ('-c', '--command')

    opts = parser.parse_args(keep)
    if collect_rest:
        opts.args = rest
    return opts

def main(logging="production"):
    from sas.system import log
    from sas.system import lib

    # Eventually argument processing might affect logger or config, so do it first
    cli = parse_cli(sys.argv)

    # Setup logger and sasmodels
    if logging == "production":
        log.production()
    elif logging == "development":
        log.development()
    else:
        raise ValueError(f"Unknown logging mode \"{logging}\"")
    lib.setup_sasmodels()
    lib.setup_qt_env() # Note: does not import any gui libraries

    if cli.version: # -V
        import sas
        print(f"SasView {sas.__version__}")

    context = {'exit': sys.exit}
    if cli.module: # -m module [arg...]
        import runpy
        # TODO: argv[0] should be the path to the module file not the dotted name
        sys.argv = [cli.module, *cli.args]
        context = runpy.run_module(cli.module, run_name="__main__")
    elif cli.command: # -c "command"
        sys.argv = ["-c", *cli.args]
        exec(cli.command, context)
    elif cli.args: # script [arg...]
        import runpy
        sys.argv = cli.args
        context = runpy.run_path(cli.args[0], run_name="__main__")
    elif not cli.interactive: # no arguments so start the GUI
        from sas.qtgui.MainWindow.MainWindow import run_sasview
        # sys.argv is unchanged
        # Maybe hand cli.quiet to run_sasview?
        run_sasview()
        return 0 # don't drop into the interactive interpreter

    # TODO: Capture the global/local environment of the script/module
    # TODO: Start interactive with ipython rather than normal python
    # For ipython use:
    #     from IPython import start_ipython
    #     sys.argv = ["ipython", *args]
    #     sys.exit(start_ipython())
    if cli.interactive:
        import code
        exitmsg = banner = "" if cli.quiet else None
        code.interact(banner=banner, exitmsg=exitmsg, local=context)

    return 0

if __name__ == "__main__":
    sys.exit(main())
