"""HTTP-independent application state and transition rules."""
from dataclasses import dataclass, field, asdict
from threading import RLock

MAX_BYTES = 32768

class StateError(ValueError):
    pass

@dataclass(frozen=True)
class Artifact:
    revision: int
    format: str
    payload: bytes

@dataclass(frozen=True)
class Result:
    operation: str
    revision: int
    outcome: str
    text: str

@dataclass
class Model:
    source: str = ''
    name: str = 'Manual input'
    revision: int = 0
    draft: str = ''
    draft_name: str = 'Manual input'
    busy: bool = False
    results: list[Result] = field(default_factory=list)
    artifact: Artifact | None = None
    notice: str = 'Enter source or use Load source.'
    lock: RLock = field(default_factory=RLock, repr=False)

    @property
    def dirty(self):
        return self.draft != self.source or self.draft_name != self.name

    def idle(self):
        if self.busy:
            raise StateError('Busy: wait for the current operation.')

    def clean(self):
        self.idle()
        if self.dirty:
            raise StateError('Apply or discard changes first.')

    def edit(self, text):
        self.idle()
        self.draft = text
        self.notice = 'Unapplied changes.' if self.dirty else 'Ready.'

    def discard(self):
        self.idle()
        self.draft, self.draft_name = self.source, self.name
        self.notice = 'Changes discarded.'

    def apply(self):
        self.idle()
        if not self.draft.strip():
            raise StateError('Source cannot be empty or whitespace only.')
        try:
            size = len(self.draft.encode('utf-8'))
        except UnicodeError as exc:
            raise StateError('Source must be valid UTF-8.') from exc
        if size > MAX_BYTES:
            raise StateError(f'Source exceeds {MAX_BYTES} UTF-8 bytes.')
        self.source, self.name = self.draft, self.draft_name
        self.revision += 1
        self.results.clear()
        self.artifact = None
        self.notice = 'Source applied.'

    def manual(self):
        self.clean()
        self.draft, self.draft_name = '', 'Manual input'
        self.notice = 'Enter code, then Apply changes.'

    def replace(self, text, name):
        self.clean()
        self.draft, self.draft_name = text, name
        self.apply()  # failed validation deliberately retains the rejected draft

    def begin(self, operation):
        self.clean()
        if not self.revision:
            raise StateError('Apply source before running tools.')
        if operation == 'execute' and (self.artifact is None or self.artifact.revision != self.revision):
            raise StateError('Execute needs generated code; compilation is not yet implemented.')
        if operation == 'compile':
            self.artifact = None
        self.busy = True
        self.notice = f'Busy: {operation} on revision {self.revision}.'

    def finish(self, result):
        if result.revision != self.revision:
            raise StateError('Backend returned a stale revision.')
        self.results.append(result)
        self.busy = False
        self.notice = 'Ready. You can edit or retry.'

    def snapshot(self):
        return dict(source=self.source, draft=self.draft, name=self.name,
                    revision=self.revision, dirty=self.dirty, busy=self.busy,
                    notice=self.notice, results=[asdict(r) for r in self.results],
                    executable=self.artifact is not None and self.artifact.revision == self.revision)
