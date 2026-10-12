import unittest
from domain import AUDIT, get_order, calculate_exception, draft_customer_message, request_escalation

class OrderAgentTests(unittest.TestCase):
    def setUp(self):
        AUDIT.clear()
    def test_shortage_and_approval(self):
        a=calculate_exception('SO-1001')
        self.assertEqual(a['shortage'],22)
        self.assertTrue(a['requires_approval'])
    def test_available_order(self):
        a=calculate_exception('SO-1002')
        self.assertEqual(a['shortage'],0)
        self.assertFalse(a['at_risk'])
    def test_unknown_order(self):
        self.assertEqual(get_order('BAD')['error'],'order_not_found')
    def test_approval_denied(self):
        r=request_escalation('SO-1001','request',approved=False)
        self.assertFalse(r['executed'])
        self.assertEqual(AUDIT[-1]['result'],'DENIED')
    def test_no_send(self):
        self.assertEqual(draft_customer_message('SO-1001')['status'],'draft_only')

if __name__=='__main__': unittest.main()
