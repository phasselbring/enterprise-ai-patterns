"""Gateway tests assert handler non-execution on denial, not merely a denied message."""
import asyncio
import pytest
from enterprise_ai_patterns.governance.authorization import ExecutionPrincipal, AuthorizationDenied
from enterprise_ai_patterns.governance.approval import ApprovalDenied, require_approval
from enterprise_ai_patterns.governance.execution_gateway import ExecutionGateway
from enterprise_ai_patterns.governance.idempotency import ResultStoreAdapter


class Verifier:
    def __init__(self, allowed): self.allowed=allowed; self.seen=[]
    def verify(self, **kwargs): self.seen.append(kwargs); return self.allowed


def fixture_gateway(*, permitted=True, protected=False, verifier=None, failing=False):
    calls=[]; audit=[]
    async def handler(args):
        calls.append(args)
        if failing: raise RuntimeError('downstream failure')
        return {'ok':True}
    gateway=ExecutionGateway({'update_order':handler}, audit=audit.append,
        approval_verifier=verifier, protected_tools=frozenset({'update_order'} if protected else ()))
    principal=ExecutionPrincipal('alice',frozenset({'update_order'} if permitted else ()))
    return gateway,principal,calls,audit


def execute(gw, principal, name='update_order'):
    return asyncio.run(gw.execute(principal,name,{'order_id':'SO-1001'},action_id='action1',resource_id='SO-1001'))


def test_authorized_action_audits_completion():
    gw,p,calls,audit=fixture_gateway()
    assert execute(gw,p)=={'ok':True}
    assert calls==[{'order_id':'SO-1001'}]
    assert [x['event'] for x in audit]==['tool_completed']


def test_unauthorized_action_never_invokes_handler():
    gw,p,calls,audit=fixture_gateway(permitted=False)
    with pytest.raises(AuthorizationDenied): execute(gw,p)
    assert calls==[] and audit[0]['event']=='tool_blocked_or_failed'


def test_unregistered_tool_denied_even_if_principal_allows_it():
    gw,p,calls,audit=fixture_gateway()
    p=ExecutionPrincipal('alice',frozenset({'nonexistent'}))
    with pytest.raises(PermissionError): execute(gw,p,'nonexistent')
    assert calls==[] and audit[0]['event']=='tool_blocked_or_failed'


@pytest.mark.parametrize('verifier',[None,Verifier(False)])
def test_protected_action_denied_without_independent_approval(verifier):
    gw,p,calls,audit=fixture_gateway(protected=True,verifier=verifier)
    with pytest.raises(PermissionError): execute(gw,p)
    assert calls==[]
    assert audit[0]['event']=='tool_blocked_or_failed'
    if verifier: assert verifier.seen==[{'caller_id':'alice','action_id':'action1','resource_id':'SO-1001'}]


def test_approved_action_executes_after_verification():
    verifier=Verifier(True)
    gw,p,calls,audit=fixture_gateway(protected=True,verifier=verifier)
    assert execute(gw,p)=={'ok':True}
    assert len(calls)==1 and audit[0]['event']=='tool_completed'


def test_tool_failure_is_audited():
    gw,p,calls,audit=fixture_gateway(failing=True)
    with pytest.raises(RuntimeError): execute(gw,p)
    assert len(calls)==1 and audit[0]['error']=='RuntimeError'


def test_require_approval_denies_bad_decision():
    with pytest.raises(ApprovalDenied):
        require_approval(Verifier(False),caller_id='alice',action_id='a',resource_id='r')


def test_idempotency_facade_put_get_and_missing():
    store=ResultStoreAdapter()
    assert store.get('unknown') is None
    store.put('key','result')
    assert store.get('key')=='result'
