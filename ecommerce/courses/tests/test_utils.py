import hashlib

import ddt
import httpretty

from django.core.cache import cache

from ecommerce.core.constants import ENROLLMENT_CODE_SWITCH
from ecommerce.core.tests import toggle_switch
from ecommerce.core.tests.decorators import mock_course_catalog_api_client
from ecommerce.coupons.tests.mixins import CourseCatalogMockMixin
from ecommerce.courses.models import Course
from ecommerce.courses.tests.factories import CourseFactory
from ecommerce.courses.utils import (
    get_certificate_type_display_value, get_course_info_from_catalog, mode_for_seat
)
from ecommerce.extensions.catalogue.tests.mixins import CourseCatalogTestMixin
from ecommerce.tests.testcases import TestCase


@httpretty.activate
@ddt.ddt
class UtilsTests(CourseCatalogTestMixin, CourseCatalogMockMixin, TestCase):
    @ddt.unpack
    @ddt.data(
        ('', False, 'audit'),
        ('honor', True, 'honor'),
        ('honor', False, 'honor'),
        ('verified', True, 'verified'),
        ('verified', False, 'verified'),
        ('professional', True, 'professional'),
        ('professional', False, 'no-id-professional'),
        ('no-id-professional', False, 'no-id-professional'),
    )
    def test_mode_for_seat(self, certificate_type, id_verification_required, mode):
        """ Verify the correct enrollment mode is returned for a given seat. """
        course = Course.objects.create(id='edx/Demo_Course/DemoX')
        toggle_switch(ENROLLMENT_CODE_SWITCH, True)
        seat = course.create_or_update_seat(certificate_type, id_verification_required, 10.00, self.partner)
        self.assertEqual(mode_for_seat(seat), mode)
        enrollment_code = course.enrollment_code_product
        if enrollment_code:  # We should only have enrollment codes for allowed types
            self.assertEqual(mode_for_seat(enrollment_code), mode)

    @mock_course_catalog_api_client
    def test_get_course_info_from_catalog(self):
        """ Check to see if course info gets cached """
        course = CourseFactory()
        self.mock_dynamic_catalog_single_course_runs_api(course)

        cache_key = 'courses_api_detail_{}{}'.format(course.id, self.site.siteconfiguration.partner.short_code)
        cache_hash = hashlib.md5(cache_key).hexdigest()
        cached_course = cache.get(cache_hash)
        self.assertIsNone(cached_course)

        response = get_course_info_from_catalog(self.request.site, course)

        self.assertEqual(response['title'], course.name)

        cached_course = cache.get(cache_hash)
        self.assertEqual(cached_course, response)

    @ddt.data(
        ('honor', 'Honor'),
        ('verified', 'Verified'),
        ('professional', 'Professional'),
        ('audit', 'Audit')
    )
    @ddt.unpack
    def test_cert_display(self, cert_type, cert_display):
        """ Verify certificate display types. """
        self.assertEqual(get_certificate_type_display_value(cert_type), cert_display)

    def test_cert_display_assertion(self):
        """ Verify assertion for invalid cert type """
        self.assertRaises(ValueError, lambda: get_certificate_type_display_value('junk'))
