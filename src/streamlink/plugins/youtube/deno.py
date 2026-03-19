"""Deno-backed JavaScript challenge solver for the YouTube plugin.

:class:`DenoJCP` spawns a sandboxed ``deno run`` subprocess, feeds it the
YouTube player JS bundle together with the bundled ``lib`` / ``core`` solver
scripts, and parses the JSON result to produce a solved
:class:`NChallengeOutput`.
"""

import json
import logging
import os
import shlex
import subprocess

from . import solver
from .structures import ctx, NChallengeInput, NChallengeOutput

log = logging.getLogger(__name__)


class DenoJCP:
    """Solves YouTube n-parameter challenges by executing JS inside Deno."""

    def __init__(self):
        # player_url -> raw JS source text
        self._code_cache: dict[str, str] = {}

    @staticmethod
    def validate_response(response: NChallengeOutput, request: NChallengeInput) -> bool | str:
        """Validate that *response* is a well-formed, successful challenge result.

        A result is considered invalid when:

        - *response* is not an :class:`NChallengeOutput` instance.
        - Any key or value in ``results`` is not a plain string.
        - The original token is absent from ``results``.
        - A result value ends with the original challenge token, which indicates
          the YouTube JS solver function raised an internal exception and echoed
          the input back as the output.

        Args:
            response: Output produced by the Deno subprocess.
            request:  Original challenge input used to generate *response*.

        Returns:
            ``True`` when the response is valid, or an error message string
            describing the first problem found.
        """
        if not isinstance(response, NChallengeOutput):
            return "Response is not an NChallengeOutput"

        if not (
            all(isinstance(k, str) and isinstance(v, str) for k, v in response.results.items())
            and request.token in response.results
        ):
            return "Invalid NChallengeOutput: missing token or non-string entries"

        # When the JS solver throws internally it returns the input token as the
        # result, so a result that ends with the original challenge is a failure.
        for challenge, result in response.results.items():
            if result.endswith(challenge):
                return f"n result is invalid for {challenge!r}: {result!r}"

        return True

    @staticmethod
    def _get_script(script_type: str) -> str:
        """Load a bundled solver script by name.

        Args:
            script_type: Either ``"core"`` or ``"lib"``.

        Returns:
            JS source string for the requested script.

        Raises:
            ValueError: If the script cannot be loaded from the package.
        """
        try:
            return solver.core() if script_type == "core" else solver.lib()
        except Exception as exc:
            raise ValueError(
                f'Failed to load solver "{script_type}" script from package: {exc}'
            ) from exc

    def _construct_stdin(self, player: str, request: NChallengeInput) -> str:
        """Build the JS source string that is piped to the Deno process.

        Inlines the ``lib`` and ``core`` solver scripts, then calls the
        exported ``jsc`` function with a JSON-serialized request payload.

        Args:
            player:  Raw YouTube player JS source code.
            request: Challenge input containing the token to solve.

        Returns:
            Multi-line JS string ready to be written to the subprocess stdin.
        """
        data = {
            "type": "player",
            "player": player,
            "requests": [{"type": "n", "challenges": [request.token]}],
            "output_preprocessed": True,
        }
        return (
            f"{self._get_script('lib')}\n"
            f"Object.assign(globalThis, lib);\n"
            f"{self._get_script('core')}\n"
            f"console.log(JSON.stringify(jsc({json.dumps(data)})));\n"
        )

    def _run_js_runtime(self, player: str, request: NChallengeInput) -> str:
        """Spawn a Deno process, pipe the solver script to it, and return stdout.

        The process runs with network access, npm, remote imports, and the
        module cache all disabled so that only the bundled solver scripts and
        the provided player source are executed.

        Args:
            player:  Raw YouTube player JS source code.
            request: Challenge input whose token will be solved.

        Returns:
            Raw stdout string from the Deno process (JSON-encoded result).

        Raises:
            Exception: If the process exits with a non-zero return code or
                       writes anything to stderr.
            BaseException: Re-raised as-is (e.g. ``KeyboardInterrupt``) after
                           the subprocess is forcibly terminated.
        """
        stdin = self._construct_stdin(player, request)
        cmd = [
            "deno", "run",
            "--ext=js",
            "--no-code-cache",
            "--no-prompt",
            "--no-remote",
            "--no-lock",
            "--node-modules-dir=none",
            "--no-config",
            "--no-npm",
            "--cached-only",
            "-",
        ]
        log.debug("Executing Deno: %s", shlex.join(cmd))

        proc = subprocess.Popen(
            cmd,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=os.environ.copy(),
            encoding="utf-8",
        )
        try:
            stdout, stderr = proc.communicate(stdin)
        except BaseException:
            proc.kill()
            proc.wait(timeout=0)
            raise

        if proc.returncode or stderr:
            msg = f"Deno process failed (returncode: {proc.returncode})"
            if stderr:
                msg = f"{msg}: {stderr.strip()}"
            raise Exception(msg)

        log.debug("Deno process completed successfully")
        return stdout

    def _get_player(self, player_url: str) -> str | None:
        """Return the player JS source for *player_url*, fetching and caching on first access.

        Args:
            player_url: Absolute URL of the YouTube player JS bundle.

        Returns:
            JS source string, or ``None`` if the response body was empty.
        """
        if player_url not in self._code_cache:
            log.debug("Fetching player JS: %s", player_url)
            code = ctx.session.http.get(player_url).text
            if code:
                self._code_cache[player_url] = code
                log.debug("Player JS cached (%d chars)", len(code))
            else:
                log.warning("Empty response for player JS URL: %s", player_url)
        return self._code_cache.get(player_url)

    def solve(self, challenge: NChallengeInput) -> NChallengeOutput | None:
        """Solve a single YouTube n-parameter challenge using Deno.

        Fetches (or retrieves from cache) the player JS, runs the bundled
        solver inside a sandboxed Deno subprocess, and validates the result
        before returning it.

        Args:
            challenge: Input containing the player URL and the raw ``n`` token.

        Returns:
            :class:`NChallengeOutput` with the solved token mapping,
            or ``None`` if an error occurs at any stage.
        """
        log.debug("Solving n-challenge token %r via Deno", challenge.token)
        try:
            player = self._get_player(challenge.player_url)
            if not player:
                log.error("Could not retrieve player JS for URL: %s", challenge.player_url)
                return None

            stdout = self._run_js_runtime(player, challenge)
            output = json.loads(stdout)

            if output.get("type") == "error":
                raise Exception(f"Solver top-level error: {output['error']}")

            response_data = output["responses"][0]
            if response_data.get("type") == "error":
                raise Exception(
                    f"Solver response error for challenge {challenge!r}: {response_data['error']}"
                )

            response = NChallengeOutput(response_data["data"])
            log.debug("Raw solver response: %s", response)

            if (validation_msg := self.validate_response(response, challenge)) is not True:
                log.warning("Invalid n-challenge response from Deno: %s", validation_msg)

            return response

        except Exception as exc:
            log.error("n-challenge solving failed for token %r: %s", challenge.token, exc)
            if 'The system cannot find the file specified' in str(exc):
                raise Exception("Deno not found. "
                                "Please install Deno from https://deno.land/manual/getting_started/installation")
            return NChallengeOutput(results={})
