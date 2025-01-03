import sys
from typing import Any, Iterator, override, Tuple

from xonsh.built_ins import XSH
from xonsh.completer import Completer
from xonsh.completers.tools import RichCompletion
from xonsh.parsers.completion_context import CompletionContext

from kmd.config.logger import get_logger
from kmd.xontrib.completion_ranking import normalize, sort_by_prefix_display, sort_default

log = get_logger(__name__)


class RankingCompleter(Completer):
    """
    Custom completer that overrides default xonsh behavior to provide better
    control over completion ranking and deduplication.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @override
    def complete_from_context(
        self, completion_context: CompletionContext, old_completer_args=None
    ) -> Tuple[Tuple[RichCompletion, ...], int]:
        self._get_settings()
        self._trace("Getting completions with context:", completion_context)

        # Collect all completions.
        completions = tuple(self._collect_completions(completion_context, old_completer_args))
        # self._trace("Collected completions:", completions)

        # Deduplicate.
        unique_completions = self._deduplicate_completions(completions)

        # Rank.
        ranked_completions = self._rank_completions(unique_completions, completion_context)

        # lprefix is the length of the prefix of the last completion.
        lprefix = len(ranked_completions[0].value) if ranked_completions else 0

        return ranked_completions, lprefix

    def _collect_completions(
        self, completion_context: CompletionContext, old_completer_args
    ) -> Iterator[RichCompletion]:
        """
        Collect completions from all registered completers. Ensure all are
        RichCompletions.
        """
        count = 0

        for completion, prefix_len in self.generate_completions(
            completion_context, old_completer_args, trace=self.trace
        ):
            if not isinstance(completion, RichCompletion):
                prefix_len = prefix_len or len(completion)
                completion = RichCompletion(completion, prefix_len=prefix_len)
            yield completion
            count += 1
            if self.query_limit and count >= self.query_limit:
                self._trace(f"Stopped after {self.query_limit} completions reached.")
                break

    def _deduplicate_completions(
        self, completions: Tuple[RichCompletion, ...]
    ) -> Tuple[RichCompletion, ...]:
        """
        Deduplicate completions while preserving order.
        """

        seen_values = set()
        deduped_completions = []
        for completion in completions:
            c_str = normalize(completion)
            if c_str not in seen_values:
                seen_values.add(c_str)
                deduped_completions.append(completion)

        if len(deduped_completions) < len(completions):
            self._trace(
                f"Deduplicated completions kept {len(deduped_completions)}/{len(completions)}:",
                deduped_completions,
            )
        else:
            self._trace(f"No duplicates found in {len(completions)} completions.")

        return tuple(deduped_completions)

    def _rank_completions(
        self,
        completions: Tuple[RichCompletion, ...],
        context: CompletionContext,
    ) -> Tuple[RichCompletion, ...]:
        if context and context.command:
            sortkey = sort_by_prefix_display(context.command.prefix)
        else:
            sortkey = sort_default()

        return tuple(sorted(completions, key=sortkey))

    def _get_settings(self):
        assert XSH.env
        self.trace = bool(XSH.env.get("XONSH_TRACE_COMPLETIONS"))
        self.query_limit = int(str(XSH.env.get("COMPLETION_QUERY_LIMIT", 0)))

    def _trace(self, msg: str, value: Any = None):
        if self.trace:
            print(f"RANKING COMPLETER: {msg}")
            if value is not None:
                sys.displayhook(value)
