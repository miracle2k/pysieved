#! /usr/bin/python

import unittest
import dovecot
import dovecot_single
import tempfile
import os

class TestDovecot(unittest.TestCase):
    def setUp(self):
        self.homedir = tempfile.mkdtemp()


    def tearDown(self):
        os.system('rm -rf %s' % self.homedir)


    def testStorage(self):
        s = dovecot.ScriptStorage('/usr/lib/dovecot/sievec',
                                  '.pysieved',
                                  self.homedir)
        d = os.path.join(self.homedir, '.pysieved')
        self.failUnless(os.path.isdir(d))
        self.failIf(os.path.exists(os.path.join(d, 'dovecot')))
        self.failIf(os.path.islink(os.path.join(self.homedir,
                                                '.dovecot.sieve')))

        def setit(k, v):
            s[k] = v
        def getit(k):
            return s[k]
        def delit(k):
            del s[k]
        script = 'if header :is "subject" "junkme" { discard; }'

        # Raise some exceptions
        self.failUnlessRaises(ValueError, setit, 'foo', 'fubbajubba')
        self.failUnlessRaises(KeyError, getit, 'foo')
        self.failUnlessRaises(KeyError, s.set_active, 'foo')
        self.failUnlessRaises(KeyError, s.is_active, 'foo')

        # Set a real script
        s['foo'] = script
        self.failUnlessEqual(s['foo'], script)
        self.failUnlessEqual([sn for sn in s], ['foo'])
        self.failUnless(os.path.exists(os.path.join(d, 'foo')))

        # Make it active
        s.set_active('foo')
        self.failUnless(s.is_active('foo'))
        self.failUnlessEqual([sn for sn in s], ['foo'])
        self.failUnless(os.path.islink(os.path.join(self.homedir,
                                                    '.dovecot.sieve')))

        # Delete it
        self.failUnlessRaises(ValueError, delit, 'foo')
        s.set_active(None)
        del s['foo']
        self.failIf(os.path.exists(os.path.join(d, 'foo')))
        self.failIf(os.path.exists(os.path.join(self.homedir,
                                                '.dovecot.sieve')))

        # Now let's try having several
        s['1'] = script
        s['2'] = script
        s['3'] = script
        l = [sn for sn in s]
        l.sort()
        self.failUnlessEqual(l, ['1', '2', '3'])

        # Fiddle with active script
        for i in l:
            s.set_active(i)
            for j in l:
                if i == j:
                    self.failUnless(s.is_active(i))
                else:
                    self.failIf(s.is_active(j))


    def testSingle(self):
        s = dovecot_single.ScriptStorage('/usr/lib/dovecot/sievec',
                                         self.homedir,
                                         'froobjoob')

        self.failIf(os.path.islink(os.path.join(self.homedir,
                                                '.dovecot.sieve')))

        def setit(k, v):
            s[k] = v
        def getit(k):
            return s[k]
        def delit(k):
            del s[k]
        script = 'if header :is "subject" "junkme" { discard; }'

        # Raise some exceptions
        self.failUnlessRaises(ValueError, setit, 'froobjoob', 'fubbajubba')
        self.failUnlessRaises(KeyError, getit, 'froobjoob')
        self.failUnlessRaises(KeyError, s.set_active, 'froobjoob')
        self.failIf(s.is_active('froobjoob'))

        # Set a real script
        s['froobjoob'] = script
        self.failUnlessEqual(s['froobjoob'], script)
        self.failUnlessEqual([sn for sn in s], ['froobjoob'])
        self.failUnless(os.path.exists(os.path.join(self.homedir,
                                                    '.dovecot.sieve')))

        # Make it active
        s.set_active('froobjoob')
        self.failUnless(s.is_active('froobjoob'))
        self.failUnlessEqual([sn for sn in s], ['froobjoob'])
        self.failUnless(os.path.exists(os.path.join(self.homedir,
                                                    '.dovecot.sieve')))

        # Delete it
        self.failUnlessRaises(KeyError, s.set_active, None)
        self.failUnlessRaises(KeyError, delit, 'foo')
        del s['froobjoob']
        self.failIf(os.path.exists(os.path.join(self.homedir,
                                                '.dovecot.sieve')))

