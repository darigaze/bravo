from twisted.trial import unittest

from twisted.internet import reactor
from twisted.internet.task import deferLater

from construct import Container

from bravo.errors import BetaClientError
import bravo.protocols.beta

class FakeTransport(object):

    data = []
    lost = False

    def write(self, data):
        self.data.append(data)

    def loseConnection(self):
        self.lost = True

class TestBetaServerProtocol(unittest.TestCase):

    def setUp(self):
        self.p = bravo.protocols.beta.BetaServerProtocol()
        self.p.transport = FakeTransport()

    def tearDown(self):
        # Stop the connection timeout.
        if self.p._TimeoutMixin__timeoutCall:
            self.p._TimeoutMixin__timeoutCall.cancel()

    def test_trivial(self):
        pass

    def test_location_update(self):
        """
        Regression test for location unification commits around the time of
        5a14768866cdebdb022a69b9edbed22208550033.
        """

        # This packet is the location test packet from the packet parser
        # test suite.
        location_packet = """
        DT/wAAAAAAAAQAAAAAAAAABACAAAAAAAAEAQAAAAAAAAQKAAAEDAAAAB
        """.decode("base64")

        self.p.dataReceived(location_packet)

        self.assertEqual(self.p.location.x, 1)
        self.assertEqual(self.p.location.y, 2)
        self.assertEqual(self.p.location.stance, 3)
        self.assertEqual(self.p.location.z, 4)
        self.assertEqual(self.p.location.yaw, 5)
        self.assertEqual(self.p.location.pitch, 6)
        self.assertTrue(self.p.location.grounded)

    def test_reject_ancient_and_newfangled_clients(self):
        """
        Directly test the login() method for client protocol checking.
        """

        error_called = [False]
        def error(reason):
            error_called[0] = True
        self.patch(self.p, "error", error)

        container = Container()
        container.protocol = 1
        self.p.login(container)

        self.assertTrue(error_called[0])

        error_called[0] = False

        container = Container()
        container.protocol = 42
        self.p.login(container)

        self.assertTrue(error_called[0])

    def test_health_initial(self):
        """
        The client's health should start at 20.
        """

        self.assertEqual(self.p.health, 20)

    def test_health_invalid(self):
        """
        An error is raised when an invalid value is assigned for health.
        """

        self.assertRaises(BetaClientError, setattr, self.p, "health", -1)
        self.assertRaises(BetaClientError, setattr, self.p, "health", 21)

    def test_health_update(self):
        """
        The protocol should emit a health update when its health changes.
        """

        # Health packet, 19 health
        expected = "\x08\x00\x13"

        self.p.transport.data = []
        self.p.health = 19
        self.assertEqual(len(self.p.transport.data), 1)
        self.assertEqual(self.p.transport.data[0], expected)

    def test_health_no_change(self):
        """
        If health is assigned to but not changed, no health update should be
        issued.
        """

        self.p.transport.data = []
        self.p.health = 20
        self.assertFalse(self.p.transport.data)

    def test_connection_timeout(self):
        """
        Connections should time out after 30 seconds.
        """

        def cb():
            self.assertTrue(self.p.transport.lost)

        d = deferLater(reactor, 31, cb)
        return d


class TestBravoProtocol(unittest.TestCase):

    def setUp(self):
        self.p = bravo.protocols.beta.BravoProtocol("unittest")

    def tearDown(self):
        if self.p._TimeoutMixin__timeoutCall:
            self.p._TimeoutMixin__timeoutCall.cancel()

    def test_trivial(self):
        pass

    def test_entities_near_unloaded_chunk(self):
        """
        entities_near() shouldn't raise a fatal KeyError when a nearby chunk
        isn't loaded.

        Reported by brachiel on IRC.
        """

        list(self.p.entities_near(2))
