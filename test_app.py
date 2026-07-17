import unittest
import json
import os
import app as flask_app
import database

class BattleBitsTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        flask_app.app.config['TESTING'] = True
        flask_app.app.config['WTF_CSRF_ENABLED'] = False
        self.client = flask_app.app.test_client()
        
        # Ensure clean database path
        database.init_db()

    def test_database_init(self):
        self.assertTrue(os.path.exists(database.DB_PATH))

    def test_user_registration_and_login(self):
        # 1. Register a user
        response = self.client.post('/cadastro', data={
            'usuario': 'testuser',
            'email': 'test@example.com',
            'senha': 'password123',
            'confirmar_senha': 'password123'
        }, follow_redirects=True)
        self.assertIn(b'testuser', response.data)
        
        # 2. Login user
        response = self.client.post('/login', data={
            'usuario': 'testuser',
            'senha': 'password123'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        # Verify user is in session
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get('username'), 'testuser')

    def test_cart_operations(self):
        # Add item to cart
        response = self.client.post('/api/cart/add', 
            data=json.dumps({'id': 'vip-1', 'type': 'vip', 'quantity': 2}),
            content_type='application/json'
        )
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertEqual(data['total_items'], 2)
        
        # Get count
        response = self.client.get('/api/cart/count')
        data = json.loads(response.data)
        self.assertEqual(data['total_items'], 2)
        
        # Remove item
        response = self.client.post('/api/cart/remove',
            data=json.dumps({'id': 'vip-1', 'type': 'vip'}),
            content_type='application/json'
        )
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        
        # Clear cart
        response = self.client.post('/api/cart/clear')
        data = json.loads(response.data)
        self.assertTrue(data['success'])

if __name__ == '__main__':
    unittest.main()
