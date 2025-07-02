import datetime
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from datetime import timezone as dt_timezone                                        

import stripe
from payments.utils.extract_stripe_refund_data import extract_stripe_refund_data


@override_settings(STRIPE_SECRET_KEY='sk_test_mock_key')
class ExtractStripeRefundDataTestCase(TestCase):
    #--

    def setUp(self):
        #--
                                                                            
                                                                
                                                       
        self.mock_now = datetime.datetime(2023, 1, 15, 10, 0, 0, tzinfo=dt_timezone.utc)
        self.mock_now_patch = mock.patch('django.utils.timezone.now', return_value=self.mock_now)
        self.mock_now_patch.start()

    def tearDown(self):
        #--
        self.mock_now_patch.stop()

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_charge_object_full_refund(self, mock_stripe_charge_retrieve):
        #--
                                                                                
        mock_retrieved_charge = mock.Mock()
        mock_retrieved_charge.id = 'ch_full_refund'
        mock_retrieved_charge.amount_refunded = 10000
        mock_retrieved_charge.refunds = mock.Mock(
            data=[
                {'id': 're_full_1', 'status': 'succeeded', 'amount': 10000, 'created': self.mock_now.timestamp()}
            ]
        )

                                                                                 
        def mock_get_attribute(key, default=None):
            if key == 'id':
                return mock_retrieved_charge.id
            elif key == 'amount_refunded':
                return mock_retrieved_charge.amount_refunded
            elif key == 'refunds':                                                          
                return mock_retrieved_charge.refunds
            return default

        mock_retrieved_charge.get.side_effect = mock_get_attribute
        mock_stripe_charge_retrieve.return_value = mock_retrieved_charge


        event_object_data = {
            'object': 'charge',
            'id': 'ch_full_refund',
            'amount': 10000,
            'amount_refunded': 10000,
            'refunds': {
                'object': 'list',
                'data': [
                    {'id': 're_full_1', 'status': 'succeeded', 'amount': 10000, 'created': self.mock_now.timestamp()}
                ],
                'has_more': False,
                'total_count': 1,
                'url': '/v1/charges/ch_full_refund/refunds'
            }
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('100.00'))
        self.assertEqual(result['stripe_refund_id'], 're_full_1')
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertEqual(result['charge_id'], 'ch_full_refund')
        self.assertTrue(result['is_charge_object'])
        self.assertFalse(result['is_refund_object'])

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_charge_object_partial_refund(self, mock_stripe_charge_retrieve):
        #--
        latest_refund_time = self.mock_now + datetime.timedelta(minutes=5)

        mock_retrieved_charge = mock.Mock()
        mock_retrieved_charge.id = 'ch_partial_refund'
        mock_retrieved_charge.amount_refunded = 5000
        mock_retrieved_charge.refunds = mock.Mock(
            data=[
                {'id': 're_partial_1', 'status': 'succeeded', 'amount': 3000, 'created': self.mock_now.timestamp()},
                {'id': 're_partial_2', 'status': 'succeeded', 'amount': 2000, 'created': latest_refund_time.timestamp()}
            ]
        )
        def mock_get_attribute(key, default=None):
            if key == 'id':
                return mock_retrieved_charge.id
            elif key == 'amount_refunded':
                return mock_retrieved_charge.amount_refunded
            elif key == 'refunds':
                return mock_retrieved_charge.refunds
            return default

        mock_retrieved_charge.get.side_effect = mock_get_attribute
        mock_stripe_charge_retrieve.return_value = mock_retrieved_charge


        event_object_data = {
            'object': 'charge',
            'id': 'ch_partial_refund',
            'amount': 10000,
            'amount_refunded': 5000,
            'refunds': {
                'object': 'list',
                'data': [
                    {'id': 're_partial_1', 'status': 'succeeded', 'amount': 3000, 'created': self.mock_now.timestamp()},
                    {'id': 're_partial_2', 'status': 'succeeded', 'amount': 2000, 'created': latest_refund_time.timestamp()}
                ],
                'has_more': False,
                'total_count': 2,
                'url': '/v1/charges/ch_partial_refund/refunds'
            }
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('50.00'))
        self.assertEqual(result['stripe_refund_id'], 're_partial_2')                                 
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertEqual(result['charge_id'], 'ch_partial_refund')
        self.assertTrue(result['is_charge_object'])
        self.assertFalse(result['is_refund_object'])

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_charge_object_no_refunds(self, mock_stripe_charge_retrieve):
        #--
        mock_retrieved_charge = mock.Mock()
        mock_retrieved_charge.id = 'ch_no_refund'
        mock_retrieved_charge.amount_refunded = 0
        mock_retrieved_charge.refunds = mock.Mock(data=[])

        def mock_get_attribute(key, default=None):
            if key == 'id':
                return mock_retrieved_charge.id
            elif key == 'amount_refunded':
                return mock_retrieved_charge.amount_refunded
            elif key == 'refunds':
                return mock_retrieved_charge.refunds
            return default

        mock_retrieved_charge.get.side_effect = mock_get_attribute
        mock_stripe_charge_retrieve.return_value = mock_retrieved_charge


        event_object_data = {
            'object': 'charge',
            'id': 'ch_no_refund',
            'amount': 10000,
            'amount_refunded': 0,
            'refunds': {
                'object': 'list',
                'data': [],
                'has_more': False,
                'total_count': 0,
                'url': '/v1/charges/ch_no_refund/refunds'
            }
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('0.00'))
        self.assertIsNone(result['stripe_refund_id'])
        self.assertIsNone(result['refund_status'])
        self.assertEqual(result['charge_id'], 'ch_no_refund')
        self.assertTrue(result['is_charge_object'])
        self.assertFalse(result['is_refund_object'])

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_refund_object_with_charge_retrieve(self, mock_stripe_charge_retrieve):
        #--
                                                                                
        mock_retrieved_charge = mock.Mock()
        mock_retrieved_charge.id = 'ch_refunded_linked'
        mock_retrieved_charge.amount_refunded = 7500
        mock_retrieved_charge.refunds = mock.Mock(
            data=[
                {'id': 're_linked_1', 'status': 'succeeded', 'amount': 7500, 'created': self.mock_now.timestamp()}
            ]
        )

                                                                                 
        def mock_get_attribute(key, default=None):
            if key == 'id':
                return mock_retrieved_charge.id
            elif key == 'amount_refunded':
                return mock_retrieved_charge.amount_refunded
            elif key == 'refunds':
                return mock_retrieved_charge.refunds
            return default

        mock_retrieved_charge.get.side_effect = mock_get_attribute
        mock_stripe_charge_retrieve.return_value = mock_retrieved_charge


        event_object_data = {
            'object': 'refund',
            'id': 're_linked_1',
            'status': 'succeeded',
            'amount': 7500,                                          
            'charge': 'ch_refunded_linked',
            'created': self.mock_now.timestamp()
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('75.00'))                                             
        self.assertEqual(result['stripe_refund_id'], 're_linked_1')
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertEqual(result['charge_id'], 'ch_refunded_linked')
        self.assertFalse(result['is_charge_object'])
        self.assertTrue(result['is_refund_object'])

    @mock.patch('stripe.Charge.retrieve', side_effect=stripe.error.StripeError("Charge not found"))
    def test_extract_from_refund_object_charge_retrieve_fails(self, mock_stripe_charge_retrieve):
        #--
        event_object_data = {
            'object': 'refund',
            'id': 're_failed_charge_lookup',
            'status': 'failed',
            'amount': 2500,                                          
            'charge': 'ch_missing',
            'created': self.mock_now.timestamp()
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('25.00'))                                       
        self.assertEqual(result['stripe_refund_id'], 're_failed_charge_lookup')
        self.assertEqual(result['refund_status'], 'failed')
        self.assertEqual(result['charge_id'], 'ch_missing')
        self.assertFalse(result['is_charge_object'])
        self.assertTrue(result['is_refund_object'])
                                                      
        mock_stripe_charge_retrieve.assert_called_once_with('ch_missing')

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_refund_object_no_charge_id(self, mock_stripe_charge_retrieve):
        #--
        event_object_data = {
            'object': 'refund',
            'id': 're_no_charge',
            'status': 'succeeded',
            'amount': 5000,
            'charge': None,                
            'created': self.mock_now.timestamp()
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('50.00'))
        self.assertEqual(result['stripe_refund_id'], 're_no_charge')
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertIsNone(result['charge_id'])
        self.assertFalse(result['is_charge_object'])
        self.assertTrue(result['is_refund_object'])
        mock_stripe_charge_retrieve.assert_not_called()                                         

    def test_extract_from_unknown_object_type(self):
        #--
        event_object_data = {
            'object': 'payment_intent',
            'id': 'pi_unknown',
            'status': 'succeeded',
            'amount': 10000,
            'created': self.mock_now.timestamp()
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('0.00'))
        self.assertIsNone(result['stripe_refund_id'])
        self.assertIsNone(result['refund_status'])
        self.assertIsNone(result['charge_id'])
        self.assertFalse(result['is_charge_object'])
        self.assertFalse(result['is_refund_object'])

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_charge_object_amount_refunded_none(self, mock_stripe_charge_retrieve):
        #--
        latest_refund_time = self.mock_now + datetime.timedelta(minutes=5)
        mock_retrieved_charge = mock.Mock()
        mock_retrieved_charge.id = 'ch_amount_refunded_none'
        mock_retrieved_charge.amount_refunded = None              
        mock_retrieved_charge.refunds = mock.Mock(
            data=[
                {'id': 're_none_amount_1', 'status': 'succeeded', 'amount': 3000, 'created': self.mock_now.timestamp()},
                {'id': 're_none_amount_2', 'status': 'succeeded', 'amount': 2000, 'created': latest_refund_time.timestamp()}
            ]
        )

        def mock_get_attribute(key, default=None):
            if key == 'id':
                return mock_retrieved_charge.id
            elif key == 'amount_refunded':
                return mock_retrieved_charge.amount_refunded
            elif key == 'refunds':
                return mock_retrieved_charge.refunds
            return default

        mock_retrieved_charge.get.side_effect = mock_get_attribute
        mock_stripe_charge_retrieve.return_value = mock_retrieved_charge


        event_object_data = {
            'object': 'charge',
            'id': 'ch_amount_refunded_none',
            'amount': 10000,
            'amount_refunded': None,                                                    
            'refunds': {
                'object': 'list',
                'data': [
                    {'id': 're_none_amount_1', 'status': 'succeeded', 'amount': 3000, 'created': self.mock_now.timestamp()},
                    {'id': 're_none_amount_2', 'status': 'succeeded', 'amount': 2000, 'created': latest_refund_time.timestamp()}
                ],
                'has_more': False,
                'total_count': 2,
                'url': '/v1/charges/ch_amount_refunded_none/refunds'
            }
        }

        result = extract_stripe_refund_data(event_object_data)
                                                                                                              
                                                                                                  
        self.assertEqual(result['refunded_amount_decimal'], Decimal('0.00'))
        self.assertEqual(result['stripe_refund_id'], 're_none_amount_2')
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertEqual(result['charge_id'], 'ch_amount_refunded_none')

    @mock.patch('stripe.Charge.retrieve')
    def test_extract_from_refund_object_charge_retrieve_amount_refunded_none(self, mock_stripe_charge_retrieve):
        #--
        mock_retrieved_charge = mock.Mock()
        mock_retrieved_charge.id = 'ch_refunded_amount_none'
        mock_retrieved_charge.amount_refunded = None                                                    
        mock_retrieved_charge.refunds = mock.Mock(data=[])                                                   

        def mock_get_attribute(key, default=None):
            if key == 'id':
                return mock_retrieved_charge.id
            elif key == 'amount_refunded':
                return mock_retrieved_charge.amount_refunded
            elif key == 'refunds':
                return mock_retrieved_charge.refunds
            return default

        mock_retrieved_charge.get.side_effect = mock_get_attribute
        mock_stripe_charge_retrieve.return_value = mock_retrieved_charge


        event_object_data = {
            'object': 'refund',
            'id': 're_charge_amount_none',
            'status': 'succeeded',
            'amount': 6000,                                          
            'charge': 'ch_refunded_amount_none',
            'created': self.mock_now.timestamp()
        }

        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('60.00'))                                       
        self.assertEqual(result['stripe_refund_id'], 're_charge_amount_none')
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertEqual(result['charge_id'], 'ch_refunded_amount_none')
        mock_stripe_charge_retrieve.assert_called_once_with('ch_refunded_amount_none')

    def test_extract_from_refund_object_amount_none(self):
        #--
        event_object_data = {
            'object': 'refund',
            'id': 're_amount_none',
            'status': 'succeeded',
            'amount': None,                              
            'charge': 'ch_some_charge',
            'created': self.mock_now.timestamp()
        }

                                                                                                   
                                                                                        
        result = extract_stripe_refund_data(event_object_data)

        self.assertEqual(result['refunded_amount_decimal'], Decimal('0.00'))
        self.assertEqual(result['stripe_refund_id'], 're_amount_none')
        self.assertEqual(result['refund_status'], 'succeeded')
        self.assertEqual(result['charge_id'], 'ch_some_charge')
