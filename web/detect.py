"""
Mobile Detect - Python detection mobile phone and tablet devices

Thanks to:
    https://github.com/serbanghita/Mobile-Detect/blob/master/Mobile_Detect.php
"""

import os
import re
import six
import json
import pkgutil
from hashlib import sha1

OPERATINGSYSTEMS = {}
DEVICE_PHONES = {}
DEVICE_TABLETS = {}
DEVICE_BROWSERS = {}
ALL_RULES = {}
ALL_RULES_EXTENDED = {}
MOBILE_HTTP_HEADERS = {}
UA_HTTP_HEADERS = {}
UTILITIES = {}


class MobileDetectRuleFileError(Exception):
    pass


class MobileDetectError(Exception):
    pass


def load_rules(filename=None):
    global OPERATINGSYSTEMS
    global DEVICE_PHONES
    global DEVICE_TABLETS
    global DEVICE_BROWSERS
    global ALL_RULES
    global ALL_RULES_EXTENDED
    global MOBILE_HTTP_HEADERS
    global UA_HTTP_HEADERS
    global UTILITIES

    if filename is None:
        rules = json.loads(pkgutil.get_data(__name__, "Mobile_Detect.json").decode())
    else:
        with open(filename) as f:
            rules = json.load(f)

    if "version" not in rules:
        raise MobileDetectRuleFileError("version not found in rule file: %s" % filename)
    if "headerMatch" not in rules:
        raise MobileDetectRuleFileError("section 'headerMatch' not found in rule file: %s" % filename)
    if "uaHttpHeaders" not in rules:
        raise MobileDetectRuleFileError("section 'uaHttpHeaders' not found in rule file: %s" % filename)
    if "uaMatch" not in rules:
        raise MobileDetectRuleFileError("section 'uaMatch' not found in rule file: %s" % filename)

    MOBILE_HTTP_HEADERS = dict((http_header, matches) for http_header, matches in six.iteritems(rules["headerMatch"]))
    UA_HTTP_HEADERS = rules['uaHttpHeaders']
    OPERATINGSYSTEMS = dict((name, re.compile(match, re.IGNORECASE|re.DOTALL)) for name, match in six.iteritems(rules['uaMatch']['os']))
    DEVICE_PHONES = dict((name, re.compile(match, re.IGNORECASE|re.DOTALL)) for name, match in six.iteritems(rules['uaMatch']['phones']))
    DEVICE_TABLETS = dict((name, re.compile(match, re.IGNORECASE|re.DOTALL)) for name, match in six.iteritems(rules['uaMatch']['tablets']))
    DEVICE_BROWSERS = dict((name, re.compile(match, re.IGNORECASE|re.DOTALL)) for name, match in six.iteritems(rules['uaMatch']['browsers']))
    UTILITIES = dict((name, re.compile(match, re.IGNORECASE | re.DOTALL)) for name, match in six.iteritems(rules['uaMatch']['utilities']))

    ALL_RULES = {}
    ALL_RULES.update(OPERATINGSYSTEMS)
    ALL_RULES.update(DEVICE_PHONES)
    ALL_RULES.update(DEVICE_TABLETS)
    ALL_RULES.update(DEVICE_BROWSERS)

    ALL_RULES_EXTENDED = {}
    ALL_RULES_EXTENDED.update(ALL_RULES)
    ALL_RULES_EXTENDED.update(UTILITIES)

    ALL_RULES_EXTENDED = dict((k.lower(), v) for k, v in six.iteritems(ALL_RULES_EXTENDED))


load_rules()


class MobileDetect(object):
    MOBILE_GRADE_A = 'A'
    MOBILE_GRADE_B = 'B'
    MOBILE_GRADE_C = 'C'
    VERSION_TYPE_FLOAT = 'float'

    properties = {
        # Build
        'Mobile': 'Mobile/[VER]',
        'Build': 'Build/[VER]',
        'Version': 'Version/[VER]',
        'VendorID': 'VendorID/[VER]',
        # Devices
        'iPad': 'iPad.*CPU[a-z ]+[VER]',
        'iPhone': 'iPhone.*CPU[a-z ]+[VER]',
        'iPod': 'iPod.*CPU[a-z ]+[VER]',
        # 'BlackBerry'  : {'BlackBerry[VER]', 'BlackBerry [VER];'},
        'Kindle': 'Kindle/[VER]',
        # Browser
        'Chrome': ['Chrome/[VER]', 'CriOS/[VER]', 'CrMo/[VER]'],
        'Coast': 'Coast/[VER]',
        'Dolfin': 'Dolfin/[VER]',
        # @reference: https:#developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent/Firefox
        'Firefox': ['Firefox/[VER]', 'FxiOS/[VER]'],
        'Fennec': 'Fennec/[VER]',
        # http:#msdn.microsoft.com/en-us/library/ms537503(v=vs.85).aspx
        # https:#msdn.microsoft.com/en-us/library/ie/hh869301(v=vs.85).aspx
        'Edge': 'Edge/[VER]',
        'IE': ['IEMobile/[VER];', 'IEMobile [VER]', 'MSIE [VER];', 'Trident/[0-9.]+;.*rv:[VER]'],
        # http:#en.wikipedia.org/wiki/NetFront
        'NetFront': 'NetFront/[VER]',
        'NokiaBrowser': 'NokiaBrowser/[VER]',
        'Opera': [' OPR/[VER]', 'Opera Mini/[VER]', 'Version/[VER]'],
        'Opera Mini': 'Opera Mini/[VER]',
        'Opera Mobi': 'Version/[VER]',
        'UC Browser': 'UC Browser[VER]',
        'MQQBrowser': 'MQQBrowser/[VER]',
        'MicroMessenger': 'MicroMessenger/[VER]',
        'baiduboxapp': 'baiduboxapp/[VER]',
        'baidubrowser': 'baidubrowser/[VER]',
        'SamsungBrowser': 'SamsungBrowser/[VER]',
        'Iron': 'Iron/[VER]',
        # @note: Safari 7534.48.3 is actually Version 5.1.
        # @note: On BlackBerry the Version is overwriten by the OS.
        'Safari': ['Version/[VER]', 'Safari/[VER]'],
        'Skyfire': 'Skyfire/[VER]',
        'Tizen': 'Tizen/[VER]',
        'Webkit': 'webkit[ /][VER]',
        'PaleMoon': 'PaleMoon/[VER]',
        # Engine
        'Gecko': 'Gecko/[VER]',
        'Trident': 'Trident/[VER]',
        'Presto': 'Presto/[VER]',
        'Goanna': 'Goanna/[VER]',
        # OS
        'iOS': ' \\bi?OS\\b [VER][ ;]{1}',
        'Android': 'Android [VER]',
        'BlackBerry': ['BlackBerry[\w]+/[VER]', 'BlackBerry.*Version/[VER]', 'Version/[VER]'],
        'BREW': 'BREW [VER]',
        'Java': 'Java/[VER]',
        # @reference: http:#windowsteamblog.com/windows_phone/b/wpdev/archive/2011/08/29/introducing-the-ie9-on-windows-phone-mango-user-agent-string.aspx
        # @reference: http:#en.wikipedia.org/wiki/Windows_NT#Releases
        'Windows Phone OS': ['Windows Phone OS [VER]', 'Windows Phone [VER]'],
        'Windows Phone': 'Windows Phone [VER]',
        'Windows CE': 'Windows CE/[VER]',
        # http:#social.msdn.microsoft.com/Forums/en-US/windowsdeveloperpreviewgeneral/thread/6be392da-4d2f-41b4-8354-8dcee20c85cd
        'Windows NT': 'Windows NT [VER]',
        'Symbian': ['SymbianOS/[VER]', 'Symbian/[VER]'],
        'webOS': ['webOS/[VER]', 'hpwOS/[VER];'],
    }

    def __init__(self, request=None, useragent=None, headers=None):
        self.request = request
        self.useragent = useragent
        self.headers = {}

        if self.request is not None:
            if self.useragent is None:
                for http_header in UA_HTTP_HEADERS:
                    if http_header in request.META:
                        self.useragent = request.META[http_header]
                        break

            for http_header, matches in six.iteritems(MOBILE_HTTP_HEADERS):
                if http_header not in request.META:
                    continue

                header_value = request.META[http_header]
                if matches and isinstance(matches, dict) and 'matches' in matches:
                    if header_value not in matches['matches']:
                        continue

                self.headers[http_header] = header_value

            if 'HTTP_X_OPERAMINI_PHONE_UA' in request.META:
                self.useragent = "%s %s" % (self.useragent, request.META['HTTP_X_OPERAMINI_PHONE_UA'])

        if headers is not None:
            self.headers.update(headers)

        if self.useragent is None:
            self.useragent = ""

        for name, prop in six.iteritems(self.properties):
            if type(prop) is not list:
                self.properties[name] = [self.properties[name]]

    def __getitem__(self, key):
        try:
            if ALL_RULES[key].search(self.useragent):
                return True
        except KeyError:
            pass
        return False

    def __contains__(self, key):
        try:
            if ALL_RULES[key].search(self.useragent):
                return True
        except KeyError:
            pass
        return False

    @property
    def device_hash(self):
        if not hasattr(self, '_device_hash'):
            hsh = sha1(self.useragent)
            for k, v in self.headers.iteritems():
                hsh.update("%s:%s" % (k, v))
            self._device_hash = hsh.hexdigest()
        return self._device_hash

    def mobile_by_headers(self):
        """
        Check the HTTP Headers for signs of mobile devices.

        This is the fastest mobile check but probably also the most unreliable.
        """

        if self.headers:
            return True

        return False

    def mobile_by_useragent(self):
        return self.is_phone() or self.is_tablet() or self.is_mobile_os() or self.is_mobile_ua()

    def is_phone(self):
        if self.detect_phone():
            return True
        return False

    def is_tablet(self):
        if self.detect_tablet():
            return True
        return False

    def is_mobile_os(self):
        if self.detect_mobile_os():
            return True
        return False

    def is_mobile_ua(self):
        if self.detect_mobile_ua():
            return True
        return False

    def detect_phone(self):
        """ Is Phone Device """
        for name, rule in six.iteritems(DEVICE_PHONES):
            if rule.search(self.useragent):
                return name
        return False

    def detect_tablet(self):
        """ Is Tabled Device """
        for name, rule in six.iteritems(DEVICE_TABLETS):
            if rule.search(self.useragent):
                return name
        return False

    def detect_mobile_os(self):
        """ Is Mobile OperatingSystem """
        for name, rule in six.iteritems(OPERATINGSYSTEMS):
            if rule.search(self.useragent):
                return name
        return False

    def detect_mobile_ua(self):
        """ Is Mobile User-Agent """
        for name, rule in six.iteritems(DEVICE_BROWSERS):
            if rule.search(self.useragent):
                return name
        return False

    def is_mobile(self):
        if self.mobile_by_headers():
            return True

        if self.mobile_by_useragent():
            return True

        return False

    def is_rule(self, rule):
        rule = rule.lower()
        if rule in ALL_RULES_EXTENDED:
            if ALL_RULES_EXTENDED[rule].search(self.useragent):
                return True
        return False

    def prepareversionno(self, ver):
        ver = ver.replace('_', '.').replace(' ', '.').replace('/', '.')
        ver_list = ver.split('.', 1)
        if len(ver_list) > 1:
            ver_list[1] = ver_list[1].replace('.', '')
        try:
            result = float('.'.join(ver_list))
        except ValueError:
            result = 0
        return result

    def version(self, property_name):
        if not property_name or property_name not in self.properties:
            return False

        for property_match_string in self.properties[property_name]:
            property_pattern = property_match_string.replace('[VER]', '([\w._\+]+)')

            matches = re.search(property_pattern, self.useragent, re.IGNORECASE | re.DOTALL)
            if matches is not None and len(matches.groups()) > 0:
                return self.prepareversionno(matches.group(1))

        return False

    def match(self, rule):
        if re.search(rule, self.useragent):
            return True
        return False

    def grade(self):
        """
        Return the browser 'grade'
        """
        isMobile = self.is_mobile()

        if (
            # Apple iOS 4-7.0 - Tested on the original iPad (4.3 / 5.0), iPad 2 (4.3 / 5.1 / 6.1), iPad 3 (5.1 / 6.0),
            # iPad Mini (6.1), iPad Retina (7.0), iPhone 3GS (4.3), iPhone 4 (4.3 / 5.1), iPhone 4S (5.1 / 6.0),
            # iPhone 5 (6.0), and iPhone 5S (7.0)
            self.is_rule('iOS') and self.version('iPad') >= 4.3 or
            self.is_rule('iOS') and self.version('iPhone') >= 4.3 or
            self.is_rule('iOS') and self.version('iPod') >= 4.3 or
            # Android 2.1-2.3 - Tested on the HTC Incredible (2.2), original Droid (2.2), HTC Aria (2.1),
            # Google Nexus S (2.3). Functional on 1.5 & 1.6 but performance may be sluggish, tested on Google G1 (1.5)
            # Android 3.1 (Honeycomb)  - Tested on the Samsung Galaxy Tab 10.1 and Motorola XOOM
            # Android 4.0 (ICS)  - Tested on a Galaxy Nexus. Note: transition performance
            # can be poor on upgraded devices
            # Android 4.1 (Jelly Bean)  - Tested on a Galaxy Nexus and Galaxy 7
            (self.version('Android') > 2.1 and self.is_rule('Webkit')) or
            # Windows Phone 7.5-8 - Tested on the HTC Surround (7.5), HTC Trophy (7.5), LG-E900 (7.5), Nokia 800 (7.8),
            # HTC Mazaa (7.8), Nokia Lumia 520 (8), Nokia Lumia 920 (8), HTC 8x (8)
            self.version('Windows Phone OS') >= 7.5 or
            # Tested on the Torch 9800 (6) and Style 9670 (6), BlackBerry Torch 9810 (7), BlackBerry Z10 (10)
            self.is_rule('BlackBerry') and self.version('BlackBerry') >= 6.0 or
            # Blackberry Playbook (1.0-2.0) - Tested on PlayBook
            self.match('Playbook.*Tablet') or
            # Palm WebOS (1.4-3.0) - Tested on the Palm Pixi (1.4), Pre (1.4), Pre 2 (2.0), HP TouchPad (3.0)
            (self.version('webOS') >= 1.4 and self.match('Palm|Pre|Pixi')) or
            # Palm WebOS 3.0  - Tested on HP TouchPad
            self.match('hp.*TouchPad') or
            # Firefox Mobile 18 - Tested on Android 2.3 and 4.1 devices
            (self.is_rule('Firefox') and self.version('Firefox') >= 18) or
            # Chrome for Android - Tested on Android 4.0, 4.1 device
            (self.is_rule('Chrome') and
                self.is_rule('AndroidOS') and
                self.version('Android') >= 4.0) or
            # Skyfire 4.1 - Tested on Android 2.3 device
            (self.is_rule('Skyfire') and
                self.version('Skyfire') >= 4.1 and
                self.is_rule('AndroidOS') and
                self.version('Android') >= 2.3) or
            # Opera Mobile 11.5-12: Tested on Android 2.3
            (self.is_rule('Opera') and
                self.version('Opera Mobi') >= 11.5 and
                self.is_rule('AndroidOS')) or
            # Meego 1.2 - Tested on Nokia 950 and N9
            self.is_rule('MeeGoOS') or
            # Tizen (pre-release) - Tested on early hardware
            self.is_rule('Tizen') or
            # Samsung Bada 2.0 - Tested on a Samsung Wave 3, Dolphin browser
            # @todo: more tests here!
            self.is_rule('Dolfin') and self.version('Bada') >= 2.0 or
            # UC Browser - Tested on Android 2.3 device
            ((self.is_rule('UC Browser') or self.is_rule('Dolfin')) and
                self.version('Android') >= 2.3) or
            # Kindle 3 and Fire  - Tested on the built-in WebKit browser for each
            (self.match('Kindle Fire') or
                self.is_rule('Kindle') and self.version('Kindle') >= 3.0) or
            # Nook Color 1.4.1 - Tested on original Nook Color, not Nook Tablet
            self.is_rule('AndroidOS') and self.is_rule('NookTablet') or
            # Chrome Desktop 16-24 - Tested on OS X 10.7 and Windows 7
            self.version('Chrome') >= 16 and not isMobile or
            # Safari Desktop 5-6 - Tested on OS X 10.7 and Windows 7
            self.version('Safari') >= 5.0 and not isMobile or
            # Firefox Desktop 10-18 - Tested on OS X 10.7 and Windows 7
            self.version('Firefox') >= 10.0 and not isMobile or
            # Internet Explorer 7-9 - Tested on Windows XP, Vista and 7
            self.version('IE') >= 7.0 and not isMobile or
            # Opera Desktop 10-12 - Tested on OS X 10.7 and Windows 7
            self.version('Opera') >= 10 and not isMobile
        ):
            return self.MOBILE_GRADE_A

        if (
            self.is_rule('iOS') and self.version('iPad') < 4.3 or
            self.is_rule('iOS') and self.version('iPhone') < 4.3 or
            self.is_rule('iOS') and self.version('iPod') < 4.3 or
            # Blackberry 5.0: Tested on the Storm 2 9550, Bold 9770
            self.is_rule('Blackberry') and self.version('BlackBerry') >= 5 and self.version(
                'BlackBerry') < 6 or
            # Opera Mini (5.0-6.5) - Tested on iOS 3.2/4.3 and Android 2.3
            (5.0 <= self.version('Opera Mini') <= 7.0 and
             (self.version('Android') >= 2.3 or self.is_rule('iOS'))) or
            # Nokia Symbian^3 - Tested on Nokia N8 (Symbian^3), C7 (Symbian^3), also works on N97 (Symbian^1)
            self.match('NokiaN8|NokiaC7|N97.*Series60|Symbian/3') or
            # @todo: report this (tested on Nokia N71)
            self.version('Opera Mobi') >= 11 and self.is_rule('SymbianOS')
        ):
            return self.MOBILE_GRADE_B

        if (
            # Blackberry 4.x - Tested on the Curve 8330
            self.version('BlackBerry') <= 5.0 or
            # Windows Mobile - Tested on the HTC Leo (WinMo 5.2)
            self.match('MSIEMobile|Windows CE.*Mobile') or self.version('Windows Mobile') <= 5.2 or
            # Tested on original iPhone (3.1), iPhone 3 (3.2)
            self.is_rule('iOS') and self.version('iPad') <= 3.2 or
            self.is_rule('iOS') and self.version('iPhone') <= 3.2 or
            self.is_rule('iOS') and self.version('iPod') <= 3.2 or
            # Internet Explorer 7 and older - Tested on Windows XP
            self.version('IE') <= 7.0 and not isMobile
        ):
            return self.MOBILE_GRADE_C

        # All older smartphone platforms and featurephones - Any device that doesn't support media queries
        # will receive the basic, C grade experience.
        return self.MOBILE_GRADE_C
