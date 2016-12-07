#===============================================================================
# Copyright (C) 2011-2012 by Andrew Moffat
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#===============================================================================



import subprocess as subp
import sys
import traceback
import os
import re
from glob import glob as original_glob
from types import ModuleType
from functools import partial
import warnings
import platform


__version__ = "0.110"
__project_url__ = "https://github.com/amoffat/pbs"

IS_PY3 = sys.version_info[0] == 3
if IS_PY3:
    raw_input = input
    unicode = str
else:
    pass

DEFAULT_ENCODING = "utf-8"

class ErrorReturnCode(Exception):
    truncate_cap = 200

    def __init__(self, full_cmd, stdout, stderr):
        self.full_cmd = full_cmd
        self.stdout = stdout
        self.stderr = stderr

        if self.stdout is None: tstdout = "<redirected>"
        else:
            tstdout = self.stdout[:self.truncate_cap]
            out_delta = len(self.stdout) - len(tstdout)
            if out_delta:
                tstdout += ("... (%d more, please see e.stdout)" % out_delta).encode()

        if self.stderr is None: tstderr = "<redirected>"
        else:
            tstderr = self.stderr[:self.truncate_cap]
            err_delta = len(self.stderr) - len(tstderr)
            if err_delta:
                tstderr += ("... (%d more, please see e.stderr)" % err_delta).encode()

        msg = "\n\nRan: %r\n\nSTDOUT:\n\n  %s\n\nSTDERR:\n\n  %s" %\
            (full_cmd, tstdout.decode(DEFAULT_ENCODING, "replace"),
             tstderr.decode(DEFAULT_ENCODING, "replace"))
        super(ErrorReturnCode, self).__init__(msg)

class CommandNotFound(Exception): pass

rc_exc_regex = re.compile("ErrorReturnCode_(\d+)")
rc_exc_cache = {}

def get_rc_exc(rc):
    rc = int(rc)
    try: return rc_exc_cache[rc]
    except KeyError: pass

    name = "ErrorReturnCode_%d" % rc
    exc = type(name, (ErrorReturnCode,), {})
    rc_exc_cache[rc] = exc
    return exc




def which(program):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program): return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def resolve_program(program):
    path = which(program)
    if not path:
        # our actual command might have a dash in it, but we can't call
        # that from python (we have to use underscores), so we'll check
        # if a dash version of our underscore command exists and use that
        # if it does
        if "_" in program: path = which(program.replace("_", "-"))
        if not path: return None
    return path


def glob(arg):
    return original_glob(arg) or arg


def create_command(cmd):
    return Command._create(cmd)


class RunningCommand(object):
    def __init__(self, command_ran, process, call_args, stdin=None):
        self.command_ran = command_ran
        self.process = process
        self._stdout = None
        self._stderr = None
        self.call_args = call_args

        # we're running in the background, return self and let us lazily
        # evaluate
        if self.call_args["bg"]:
            return

        # we're running this command as a with context, don't do anything
        # because nothing was started to run from Command.__call__
        if self.call_args["with"]: return

        # run and block
        if stdin: stdin = stdin.encode(DEFAULT_ENCODING)
        self._stdout, self._stderr = self.process.communicate(stdin)
        self._handle_exit_code(self.process.wait())

    def __enter__(self):
        # we don't actually do anything here because anything that should
        # have been done would have been done in the Command.__call__ call.
        # essentially all that has to happen is the comand be pushed on
        # the prepend stack.
        pass

    def __exit__(self, typ, value, traceback):
        if self.call_args["with"] and Command._prepend_stack:
            Command._prepend_stack.pop()

    def __str__(self):
        if IS_PY3: return self.__unicode__()
        else: return unicode(self).encode(DEFAULT_ENCODING)

    def __unicode__(self):
        if self.process:
            if self.call_args["bg"]: self.wait()
            if self._stdout: return self.stdout()
            else: return ""

    def __eq__(self, other):
        return unicode(self) == unicode(other)
    __hash__ = None  # Avoid DeprecationWarning in Python < 3

    def __contains__(self, item):
        return item in str(self)

    def __getattr__(self, p):
        # let these three attributes pass through to the Popen object
        if p in ("send_signal", "terminate", "kill"):
            if self.process: return getattr(self.process, p)
            else: raise AttributeError
        return getattr(unicode(self), p)

    def __repr__(self):
        return "<RunningCommand %r, pid:%d, special_args:%r" % (
            self.command_ran, self.process.pid, self.call_args)

    def __long__(self):
        return long(str(self).strip())

    def __float__(self):
        return float(str(self).strip())

    def __int__(self):
        return int(str(self).strip())

    def stdout(self):
        if self.call_args["bg"]: self.wait()
        return self._stdout.decode(DEFAULT_ENCODING, "replace")

    def stderr(self):
        if self.call_args["bg"]: self.wait()
        return self._stderr.decode(DEFAULT_ENCODING, "replace")

    def wait(self):
        self._stdout, self._stderr = self.process.communicate()
        self._handle_exit_code(self.process.wait())
        return str(self)

    def _handle_exit_code(self, rc):
        if rc not in self.call_args["ok_code"]:
            raise get_rc_exc(rc)(self.command_ran, self._stdout, self._stderr)

    def __len__(self):
        return len(str(self))




class Command(object):
    _prepend_stack = []

    call_args = {
        "fg": False, # run command in foreground
        "bg": False, # run command in background
        "with": False, # prepend the command to every command after it
        "out": None, # redirect STDOUT
        "err": None, # redirect STDERR
        "err_to_out": None, # redirect STDERR to STDOUT
        "in": None,
        "env": os.environ,
        "cwd": None,

        # this is for commands that may have a different exit status than the
        # normal 0.  this can either be an integer or a list/tuple of ints
        "ok_code": 0,
    }

    @classmethod
    def _create(cls, program):
        path = resolve_program(program)
        if not path: raise CommandNotFound(program)
        return cls(path)

    def __init__(self, path):
        self._path = path
        self._partial = False
        self._partial_baked_args = []
        self._partial_call_args = {}

    def __getattribute__(self, name):
        # convenience
        getattr = partial(object.__getattribute__, self)
        if name.startswith("_"): return getattr(name)
        if name == "bake": return getattr("bake")
        return getattr("bake")(name)


    @staticmethod
    def _extract_call_args(kwargs):
        kwargs = kwargs.copy()
        call_args = Command.call_args.copy()
        for parg, default in call_args.items():
            key = "_" + parg
            if key in kwargs:
                call_args[parg] = kwargs[key]
                del kwargs[key]
        return call_args, kwargs


    def _format_arg(self, arg):
        if IS_PY3:
            arg = str(arg)
        else:
            try:
                arg = unicode(arg, DEFAULT_ENCODING).encode(DEFAULT_ENCODING)
            except TypeError:
                arg = unicode(arg).encode(DEFAULT_ENCODING)

        if self._partial:
            escaped = arg.replace('"', '\\"')
            escaped = escaped.replace("$", "\$")
            escaped = escaped.replace("`", "\`")

            arg = '"{0}"'.format(escaped)

        return arg

    def _compile_args(self, args, kwargs):
        processed_args = []

        # aggregate positional args
        for arg in args:
            if isinstance(arg, (list, tuple)):
                if not arg:
                    warnings.warn("Empty list passed as an argument to %r. \
If you're using glob.glob(), please use pbs.glob() instead." % self.path, stacklevel=3)
                for sub_arg in arg: processed_args.append(self._format_arg(sub_arg))
            else: processed_args.append(self._format_arg(arg))

        # aggregate the keyword arguments
        for k,v in kwargs.items():
            # we're passing a short arg as a kwarg, example:
            # cut(d="\t")
            if len(k) == 1:
                processed_args.append("-"+k)
                if v is not True: processed_args.append(self._format_arg(v))

            # we're doing a long arg
            else:
                k = k.replace("_", "-")

                if v is True: processed_args.append("--"+k)
                else: processed_args.append("--%s=%s" % (k, self._format_arg(v)))

        return processed_args


    def bake(self, *args, **kwargs):
        fn = Command(self._path)
        fn._partial = True

        call_args, kwargs = self._extract_call_args(kwargs)

        pruned_call_args = call_args
        for k,v in Command.call_args.items():
            try:
                if pruned_call_args[k] == v:
                    del pruned_call_args[k]
            except KeyError: continue

        fn._partial_call_args.update(self._partial_call_args)
        fn._partial_call_args.update(pruned_call_args)
        fn._partial_baked_args.extend(self._partial_baked_args)
        fn._partial_baked_args.extend(fn._compile_args(args, kwargs))
        return fn

    def __str__(self):
        if IS_PY3: return self.__unicode__()
        else: return unicode(self).encode(DEFAULT_ENCODING)

    def __repr__(self):
        return str(self)

    def __unicode__(self):
        baked_args = " ".join(self._partial_baked_args)
        if baked_args: baked_args = " " + baked_args
        return self._path + baked_args

    def __eq__(self, other):
        try: return str(self) == str(other)
        except: return False
    __hash__ = None  # Avoid DeprecationWarning in Python < 3


    def __enter__(self):
        Command._prepend_stack.append([self._path])

    def __exit__(self, typ, value, traceback):
        Command._prepend_stack.pop()


    def __call__(self, *args, **kwargs):

        kwargs = kwargs.copy()
        args = list(args)

        cmd = []

        # aggregate any with contexts
        for prepend in self._prepend_stack: cmd.extend(prepend)

        cmd.append(self._path)


        call_args, kwargs = self._extract_call_args(kwargs)
        call_args.update(self._partial_call_args)


        # here we normalize the ok_code to be something we can do
        # "if return_code in call_args["ok_code"]" on
        if not isinstance(call_args["ok_code"], (tuple, list)):
            call_args["ok_code"] = [call_args["ok_code"]]

        # set pipe to None if we're outputting straight to CLI
        pipe = None if call_args["fg"] else subp.PIPE

        # check if we're piping via composition
        input_stream = pipe
        input_data = None
        if args:
            first_arg = args.pop(0)
            if isinstance(first_arg, RunningCommand):
                # it makes sense that if the input pipe of a command is running
                # in the background, then this command should run in the
                # background as well
                if first_arg.call_args["bg"]:
                    call_args["bg"] = True
                    input_stream = first_arg.process.stdout
                else:
                    input_data = first_arg.stdout()
            else: args.insert(0, first_arg)

        processed_args = self._compile_args(args, kwargs)

        # makes sure our arguments are broken up correctly
        split_args = self._partial_baked_args + processed_args
        final_args = split_args

        cmd.extend(final_args)
        command_ran = " ".join(cmd)


        # with contexts shouldn't run at all yet, they prepend
        # to every command in the context
        if call_args["with"]:
            Command._prepend_stack.append(cmd)
            return RunningCommand(command_ran, None, call_args)


        # stdin from string
        input = call_args["in"]
        if input:
            input_data = input

        # stdout redirection
        stdout = pipe
        out = call_args["out"]
        if out:
            if hasattr(out, "write"): stdout = out
            else: stdout = open(str(out), "w")

        # stderr redirection
        stderr = pipe
        err = call_args["err"]

        if err:
            if hasattr(err, "write"): stderr = err
            else: stderr = open(str(err), "w")

        if call_args["err_to_out"]: stderr = subp.STDOUT

        # leave shell=False
        process = subp.Popen(cmd, shell=False, env=call_args["env"],
            cwd=call_args["cwd"],
            stdin=input_stream, stdout=stdout, stderr=stderr)

        return RunningCommand(command_ran, process, call_args, input_data)



