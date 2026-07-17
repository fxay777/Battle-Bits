from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import database

app = Flask(__name__)
app.secret_key = 'battle-bits-super-secret-key-2026-change-in-prod'

# Initialize database
database.init_db()

@app.context_processor
def inject_user_context():
    return {
        'username': session.get('username', 'Visitante'),
        'is_admin': session.get('admin', False),
        'user_id': session.get('user_id', None)
    }

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/vips')
def vips():
    return render_template('vips.html')

@app.route('/loja')
def loja():
    try:
        with open('shop.json', 'r', encoding='utf-8') as f:
            shop_data = json.load(f)
    except Exception as e:
        print(f"Error loading shop.json: {e}")
        shop_data = {'vips': [], 'shop': []}
    
    return render_template('shop.html', vips=shop_data.get('vips', []), items=shop_data.get('shop', []))

@app.route('/carrinho')
def carrinho():
    cart = session.get('cart', {})
    cart_items = list(cart.values())
    
    # Calculate subtotal for each item and grand total
    total = 0.0
    for item in cart_items:
        item['subtotal'] = float(item['price']) * int(item['quantity'])
        total += item['subtotal']
        
    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/forum', methods=['GET', 'POST'])
def forum():
    posts_file = 'posts.json'
    is_admin = session.get('admin', False)
    username = session.get('username', 'Visitante')
    
    if request.method == 'POST':
        if is_admin:
            titulo = request.form.get('titulo')
            conteudo = request.form.get('conteudo')
            
            if titulo and conteudo:
                try:
                    posts = []
                    if os.path.exists(posts_file):
                        with open(posts_file, 'r', encoding='utf-8') as f:
                            posts = json.load(f)
                    
                    new_post = {
                        'id': len(posts) + 1,
                        'title': titulo,
                        'content': conteudo,
                        'created_by': username,
                        'is_staff': True,
                        'timestamp': datetime.now().isoformat(),
                        'comments': []
                    }
                    posts.append(new_post)
                    
                    with open(posts_file, 'w', encoding='utf-8') as f:
                        json.dump(posts, f, indent=2, ensure_ascii=False)
                    
                except Exception as e:
                    print(f'Error: {e}')
    
    try:
        if os.path.exists(posts_file):
            with open(posts_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
        else:
            posts = []
    except:
        posts = []
    
    posts.reverse()
    return render_template('forum.html', posts=posts, is_admin=is_admin, username=username)

@app.route('/forum/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    posts_file = 'posts.json'
    username = session.get('username', 'Visitante')
    
    if username == 'Visitante':
        return redirect(url_for('login'))
    
    comment_text = request.form.get('comment_text', '').strip()
    
    if comment_text:
        try:
            posts = []
            if os.path.exists(posts_file):
                with open(posts_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
            
            for post in posts:
                if post['id'] == post_id:
                    new_comment = {
                        'author': username,
                        'is_staff': session.get('admin', False),
                        'text': comment_text,
                        'timestamp': datetime.now().isoformat()
                    }
                    post['comments'].append(new_comment)
                    break
            
            with open(posts_file, 'w', encoding='utf-8') as f:
                json.dump(posts, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            print(f'Error: {e}')
    
    return redirect(url_for('forum'))

@app.route('/staffs')
def staffs():
    is_admin = session.get('admin', False)
    username = session.get('username', 'Visitante')
    return render_template('staffs.html', is_admin=is_admin, username=username)

@app.route('/novidades')
def novidades():
    return '<h1>Novidades (em desenvolvimento)</h1><a href="/">Voltar</a>', 200

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    erro = None
    sucesso = None
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        email = request.form.get('email', '').strip()
        senha = request.form.get('senha', '')
        confirmar_senha = request.form.get('confirmar_senha', '')
        
        # Validations
        if not usuario or len(usuario) < 3:
            erro = 'Nome de usuário deve ter no mínimo 3 caracteres'
        elif not email or '@' not in email:
            erro = 'Email inválido'
        elif len(senha) < 6:
            erro = 'Senha deve ter no mínimo 6 caracteres'
        elif senha != confirmar_senha:
            erro = 'As senhas não correspondem'
        else:
            # Check if user already exists
            existing_user = database.get_user_by_username(usuario)
            if existing_user:
                erro = 'Nome de usuário já está em uso'
            else:
                hashed_password = generate_password_hash(senha)
                user_id = database.create_user(usuario, email, hashed_password)
                if user_id:
                    sucesso = f'Conta criada com sucesso, {usuario}! Você pode fazer login agora.'
                else:
                    erro = 'Erro interno ao criar a conta. Tente novamente.'
    
    return render_template('cadastro.html', erro=erro, sucesso=sucesso)

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    
    # Check if there is a pending action message (like from checkout)
    info_msg = request.args.get('msg')
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        
        if not usuario or not senha:
            erro = 'Usuário e senha são obrigatórios'
        else:
            user = database.get_user_by_username(usuario)
            if user and check_password_hash(user['password_hash'], senha):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['admin'] = bool(user['is_admin'])
                
                # Redirect to checkout if cart is not empty and they came from checkout redirect
                if info_msg == 'checkout' and session.get('cart'):
                    return redirect(url_for('checkout'))
                
                return redirect(url_for('home'))
            else:
                erro = 'Usuário ou senha inválidos'
                
    return render_template('login.html', erro=erro or (info_msg == 'checkout' and 'Faça login ou cadastre-se para finalizar a sua compra.'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Cart AJAX APIs
@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    data = request.json or {}
    item_id = data.get('id')
    item_type = data.get('type')  # 'vip' or 'item'
    qty = int(data.get('quantity', 1))
    
    if not item_id or not item_type:
        return jsonify({'success': False, 'message': 'Parâmetros inválidos'}), 400
        
    try:
        with open('shop.json', 'r', encoding='utf-8') as f:
            shop_data = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erro ao ler dados da loja: {e}'}), 500
        
    # Search for item details
    item_details = None
    if item_type == 'vip':
        for v in shop_data.get('vips', []):
            if v['id'] == item_id:
                item_details = v
                break
    else:
        for item in shop_data.get('shop', []):
            if item['id'] == item_id:
                item_details = item
                break
                
    if not item_details:
        return jsonify({'success': False, 'message': 'Item não encontrado na loja'}), 404
        
    cart = session.get('cart', {})
    cart_key = f"{item_id}_{item_type}"
    
    if cart_key in cart:
        cart[cart_key]['quantity'] += qty
    else:
        cart[cart_key] = {
            'id': item_details['id'],
            'name': item_details['name'],
            'price': float(item_details['price']),
            'type': item_type,
            'quantity': qty,
            'icon': item_details.get('icon', 'fas fa-cube')
        }
        
    session['cart'] = cart
    session.modified = True
    
    total_items = sum(item['quantity'] for item in cart.values())
    return jsonify({
        'success': True,
        'message': f"{item_details['name']} adicionado ao carrinho!",
        'total_items': total_items
    })

@app.route('/api/cart/count', methods=['GET'])
def cart_count():
    cart = session.get('cart', {})
    total_items = sum(item['quantity'] for item in cart.values())
    return jsonify({'total_items': total_items})

@app.route('/api/cart/remove', methods=['POST'])
def cart_remove():
    data = request.json or {}
    item_id = data.get('id')
    item_type = data.get('type')
    
    cart = session.get('cart', {})
    cart_key = f"{item_id}_{item_type}"
    
    if cart_key in cart:
        del cart[cart_key]
        session['cart'] = cart
        session.modified = True
        return jsonify({'success': True})
        
    return jsonify({'success': False, 'message': 'Item não encontrado no carrinho'}), 404

@app.route('/api/cart/clear', methods=['POST'])
def cart_clear():
    session['cart'] = {}
    session.modified = True
    return jsonify({'success': True})

# Checkout & Payment System
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if not session.get('user_id'):
        return redirect(url_for('login', msg='checkout'))
        
    cart = session.get('cart', {})
    if not cart:
        return redirect(url_for('loja'))
        
    cart_items = list(cart.values())
    total = 0.0
    for item in cart_items:
        item['subtotal'] = float(item['price']) * int(item['quantity'])
        total += item['subtotal']
        
    if request.method == 'POST':
        payment_method = request.form.get('payment_method', 'Pix')
        
        # Save to database
        items_json = json.dumps(cart_items, ensure_ascii=False)
        database.create_purchase(
            user_id=session['user_id'],
            items_json=items_json,
            total_price=total,
            payment_method=payment_method,
            status="Aprovado"
        )
        
        # Clear cart
        session['cart'] = {}
        session.modified = True
        
        # Save checkout user for the success screen
        session['last_checkout_user'] = session.get('username')
        
        return redirect(url_for('checkout_success'))
        
    return render_template('checkout.html', cart=cart_items, total=total)

@app.route('/checkout/success')
def checkout_success():
    username = session.get('last_checkout_user') or session.get('username', 'Jogador')
    return render_template('checkout_success.html', username=username)

if __name__ == '__main__':
    app.run(debug=True)
