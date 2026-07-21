from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import mercadopago
import database

load_dotenv()  # lê o arquivo .env (NUNCA comitado) para pegar as chaves do Mercado Pago

app = Flask(__name__)
app.secret_key = 'battle-bits-super-secret-key-2026-change-in-prod'

# Initialize database
database.init_db()

# ============ MERCADO PAGO ============
# Access Token e Public Key vêm de variáveis de ambiente (.env), nunca hardcoded no código.
MP_ACCESS_TOKEN = os.environ.get('MP_ACCESS_TOKEN', '')
MP_PUBLIC_KEY = os.environ.get('MP_PUBLIC_KEY', '')
sdk = mercadopago.SDK(MP_ACCESS_TOKEN) if MP_ACCESS_TOKEN else None

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
    # A loja de itens/clantags/medalhas passou a viver dentro da aba VIPs.
    return redirect(url_for('vips'))

@app.route('/carrinho')
def carrinho():
    cart = session.get('cart', {})
    cart_items = list(cart.values())
    
    total = 0.0
    for item in cart_items:
        item['subtotal'] = float(item['price']) * int(item['quantity'])
        total += item['subtotal']

    coupon = session.get('coupon')
    discount_value = round(total * coupon['discount'], 2) if coupon else 0.0
    final_total = round(total - discount_value, 2)

    return render_template(
        'cart.html',
        cart=cart_items,
        total=total,
        final_total=final_total,
        coupon=coupon,
        discount_value=discount_value,
        mp_public_key=MP_PUBLIC_KEY,
    )

POSTS_FILE = 'posts.json'

FORUM_CATEGORIES = {
    'ideias': {
        'title': 'Aba Ideias',
        'subtitle': 'Sugira melhorias para o nosso servidor',
        'icon': 'fas fa-lightbulb',
        'desc': 'Deixe sua sugestão ou projeto para melhorar a nossa comunidade.',
        'admin_only_post': False,
    },
    'report': {
        'title': 'Aba Report / Denúncias',
        'subtitle': 'Denuncie bugs ou jogadores mal-intencionados',
        'icon': 'fas fa-bug',
        'desc': 'Encontrou trapaceiros ou falhas no mapa? Abra uma denúncia aqui para a Staff.',
        'admin_only_post': False,
    },
    'duvidas': {
        'title': 'Aba Dúvidas',
        'subtitle': 'Central de ajuda ao jogador',
        'icon': 'fas fa-question-circle',
        'desc': 'Tem alguma dúvida sobre mecânicas, compras ou comandos? Pergunte aqui.',
        'admin_only_post': False,
    },
    'novidades': {
        'title': 'Aba Novidades',
        'subtitle': 'Informativos e atualizações oficiais',
        'icon': 'fas fa-bullhorn',
        'desc': 'Fique por dentro de tudo o que nossa equipe adicionou ou alterou na rede.',
        'admin_only_post': True,
    },
}


def load_posts():
    try:
        if os.path.exists(POSTS_FILE):
            with open(POSTS_FILE, 'r', encoding='utf-8') as f:
                posts = json.load(f)
                # Compatibilidade com posts antigos sem categoria
                for p in posts:
                    p.setdefault('category', 'novidades')
                    p.setdefault('comments', [])
                return posts
    except Exception as e:
        print(f'Erro ao ler posts.json: {e}')
    return []


def save_posts(posts):
    with open(POSTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


@app.route('/forum')
def forum():
    is_admin = session.get('admin', False)
    username = session.get('username', 'Visitante')
    posts = load_posts()
    counts = {cat: sum(1 for p in posts if p.get('category') == cat) for cat in FORUM_CATEGORIES}
    return render_template('forum.html', categories=FORUM_CATEGORIES, counts=counts, is_admin=is_admin, username=username)


@app.route('/forum/<categoria>', methods=['GET', 'POST'])
def forum_categoria(categoria):
    if categoria not in FORUM_CATEGORIES:
        return redirect(url_for('forum'))

    cat_info = FORUM_CATEGORIES[categoria]
    is_admin = session.get('admin', False)
    username = session.get('username', 'Visitante')
    logged_in = username != 'Visitante'
    pode_postar = logged_in and (is_admin or not cat_info['admin_only_post'])

    if request.method == 'POST':
        if not pode_postar:
            return redirect(url_for('login'))

        titulo = request.form.get('titulo', '').strip()
        conteudo = request.form.get('conteudo', '').strip()
        if titulo and conteudo:
            posts = load_posts()
            new_id = (max([p['id'] for p in posts], default=0)) + 1
            posts.append({
                'id': new_id,
                'category': categoria,
                'title': titulo,
                'content': conteudo,
                'created_by': username,
                'is_staff': is_admin,
                'timestamp': datetime.now().isoformat(),
                'comments': [],
            })
            save_posts(posts)
        return redirect(url_for('forum_categoria', categoria=categoria))

    posts = [p for p in load_posts() if p.get('category') == categoria]
    posts.reverse()
    return render_template(
        'forum_categoria.html',
        posts=posts,
        categoria=categoria,
        cat_info=cat_info,
        pode_postar=pode_postar,
        logged_in=logged_in,
        is_admin=is_admin,
        username=username,
    )


@app.route('/forum/comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    username = session.get('username', 'Visitante')

    if username == 'Visitante':
        return redirect(url_for('login'))

    comment_text = request.form.get('comment_text', '').strip()
    posts = load_posts()
    categoria = 'ideias'

    if comment_text:
        for post in posts:
            if post['id'] == post_id:
                categoria = post.get('category', 'ideias')
                post['comments'].append({
                    'author': username,
                    'is_staff': session.get('admin', False),
                    'text': comment_text,
                    'timestamp': datetime.now().isoformat(),
                })
                break
        save_posts(posts)
    else:
        for post in posts:
            if post['id'] == post_id:
                categoria = post.get('category', 'ideias')
                break

    return redirect(url_for('forum_categoria', categoria=categoria))

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
        
        if not usuario or len(usuario) < 3:
            erro = 'Nome de usuário deve ter no mínimo 3 caracteres'
        elif not email or '@' not in email:
            erro = 'Email inválido'
        elif len(senha) < 6:
            erro = 'Senha deve ter no mínimo 6 caracteres'
        elif senha != confirmar_senha:
            erro = 'As senhas não correspondem'
        else:
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
                
                if info_msg == 'checkout' and session.get('cart'):
                    return redirect(url_for('carrinho'))
                
                return redirect(url_for('home'))
            else:
                erro = 'Usuário ou senha inválidos'
                
    return render_template('login.html', erro=erro or (info_msg == 'checkout' and 'Faça login ou cadastre-se para finalizar a sua compra.'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ============================================================
#   APIs DO CARRINHO (CORRIGIDAS – SEM DEPENDÊNCIA DO shop.json)
# ============================================================

@app.route('/api/cart/add', methods=['POST'])
def cart_add():
    """
    Adiciona um item ao carrinho usando os dados enviados pelo front‑end.
    Não valida contra shop.json, então aceita qualquer tipo (vip, clantag, medalha, etc.)
    """
    data = request.json or {}
    item_id = data.get('id')
    item_type = data.get('type')          # 'vip', 'clantag', 'medalha', etc.
    quantity = int(data.get('quantity', 1))
    name = data.get('name')
    price = data.get('price')

    # Validação mínima
    if not all([item_id, item_type, name, price is not None]):
        return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

    cart = session.get('cart', {})
    cart_key = f"{item_id}_{item_type}"

    if cart_key in cart:
        cart[cart_key]['quantity'] += quantity
    else:
        cart[cart_key] = {
            'id': item_id,
            'name': name,
            'price': float(price),
            'type': item_type,
            'quantity': quantity,
            'icon': data.get('icon', 'fas fa-cube')
        }

    session['cart'] = cart
    session.modified = True

    total_items = sum(item['quantity'] for item in cart.values())
    return jsonify({
        'success': True,
        'message': f"{name} adicionado ao carrinho!",
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

@app.route('/api/cart/update', methods=['POST'])
def cart_update():
    data = request.json or {}
    item_id = data.get('id')
    item_type = data.get('type')
    try:
        quantity = int(data.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    quantity = max(1, quantity)

    cart = session.get('cart', {})
    cart_key = f"{item_id}_{item_type}"

    if cart_key not in cart:
        return jsonify({'success': False, 'message': 'Item não encontrado no carrinho'}), 404

    cart[cart_key]['quantity'] = quantity
    session['cart'] = cart
    session.modified = True

    subtotal = float(cart[cart_key]['price']) * quantity
    total = sum(float(i['price']) * int(i['quantity']) for i in cart.values())
    return jsonify({'success': True, 'subtotal': subtotal, 'total': total})


# Códigos de apoiador válidos (demo). Pode migrar para o banco depois se quiser.
DISCOUNT_CODES = {
    'APOIA10': 0.10,
    'BATTLE15': 0.15,
}


@app.route('/api/cart/coupon', methods=['POST'])
def cart_coupon_apply():
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip().upper()

    if not code:
        return jsonify({'success': False, 'message': 'Digite um código.'}), 400

    discount = DISCOUNT_CODES.get(code)
    if discount is None:
        return jsonify({'success': False, 'message': 'Código de apoiador inválido ou expirado.'}), 404

    session['coupon'] = {'code': code, 'discount': discount}
    session.modified = True

    cart = session.get('cart', {})
    total = sum(float(i['price']) * int(i['quantity']) for i in cart.values())
    discount_value = round(total * discount, 2)

    return jsonify({
        'success': True,
        'code': code,
        'discount_percent': int(discount * 100),
        'discount_value': discount_value,
        'total': round(total - discount_value, 2),
        'message': f'Código {code} aplicado! {int(discount * 100)}% de desconto.',
    })


@app.route('/api/cart/coupon/remove', methods=['POST'])
def cart_coupon_remove():
    session.pop('coupon', None)
    session.modified = True
    cart = session.get('cart', {})
    total = sum(float(i['price']) * int(i['quantity']) for i in cart.values())
    return jsonify({'success': True, 'total': round(total, 2)})


@app.route('/api/cart/clear', methods=['POST'])
def cart_clear():
    session['cart'] = {}
    session.pop('coupon', None)
    session.modified = True
    return jsonify({'success': True})

# ============================================================
#   CHECKOUT E PAGAMENTO
# ============================================================

@app.route('/api/checkout/process', methods=['POST'])
def api_checkout_process():
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Você precisa estar logado para finalizar a compra.'}), 401

    data = request.get_json(silent=True) or {}
    nick = (data.get('nick') or '').strip()
    email = (data.get('email') or '').strip()
    nome = (data.get('nome') or '').strip()
    sobrenome = (data.get('sobrenome') or '').strip()

    if not all([nick, email, nome, sobrenome]):
        return jsonify({'success': False, 'message': 'Preencha todos os campos antes de continuar.'}), 400

    cart = session.get('cart', {})
    if not cart:
        return jsonify({'success': False, 'message': 'Seu carrinho está vazio.'}), 400

    if not sdk:
        return jsonify({
            'success': False,
            'message': 'Pagamentos indisponíveis: configure MP_ACCESS_TOKEN no arquivo .env do servidor.',
        }), 500

    cart_items = list(cart.values())
    total = 0.0
    for item in cart_items:
        item['subtotal'] = float(item['price']) * int(item['quantity'])
        total += item['subtotal']

    # Aplica o desconto do código de apoiador (se houver) proporcionalmente ao preço de cada item
    coupon = session.get('coupon')
    discount = coupon['discount'] if coupon else 0.0
    fator = round(1 - discount, 4)

    # Cria o pedido como PENDENTE. Só vira "Aprovado" quando o Mercado Pago confirmar de verdade.
    purchase_id = database.create_purchase(
        user_id=session['user_id'],
        items_json=json.dumps(cart_items, ensure_ascii=False),
        total_price=round(total * fator, 2),
        payment_method='mercadopago',
        status='pending',
        buyer_email=email,
    )

    preference_data = {
        'items': [
            {
                'title': item['name'] + (f' ({coupon["code"]})' if coupon else ''),
                'quantity': int(item['quantity']),
                'unit_price': round(float(item['price']) * fator, 2),
                'currency_id': 'BRL',
            }
            for item in cart_items
        ],
        'payer': {'name': nome, 'surname': sobrenome, 'email': email},
        'back_urls': {
            'success': url_for('checkout_success', _external=True),
            'failure': url_for('checkout_failure', _external=True),
            'pending': url_for('checkout_pending', _external=True),
        },
        'auto_return': 'approved',
        'external_reference': str(purchase_id),
        'notification_url': url_for('mp_webhook', _external=True),
        'metadata': {'nick': nick, 'purchase_id': purchase_id},
    }

    try:
        pref_response = sdk.preference().create(preference_data)
        preference = pref_response.get('response', {}) or {}
    except Exception as e:
        print(f'Erro ao criar preferência no Mercado Pago: {e}')
        return jsonify({'success': False, 'message': 'Erro ao comunicar com o Mercado Pago.'}), 500

    if pref_response.get('status') not in (200, 201) or 'id' not in preference:
        print(f'Resposta inesperada do Mercado Pago: {pref_response}')
        return jsonify({
            'success': False,
            'message': 'Não foi possível iniciar o pagamento. Verifique se o Access Token configurado é válido.',
        }), 500

    database.set_purchase_preference(purchase_id, preference.get('id'))

    # O carrinho virou um pedido pendente; esvazia para o usuário poder montar um novo
    session['cart'] = {}
    session.pop('coupon', None)
    session.modified = True

    return jsonify({
        'success': True,
        'preference_id': preference.get('id'),
        'init_point': preference.get('init_point') or preference.get('sandbox_init_point'),
    })


@app.route('/checkout/success')
def checkout_success():
    payment_id = request.args.get('payment_id') or request.args.get('collection_id')
    external_reference = request.args.get('external_reference')
    purchase = database.get_purchase_by_id(external_reference) if external_reference else None

    if purchase and sdk and payment_id:
        try:
            payment_info = sdk.payment().get(payment_id).get('response', {})
            real_status = payment_info.get('status', 'pending')
            database.update_purchase_status(purchase['id'], real_status, payment_id)
        except Exception as e:
            print(f'Erro ao consultar pagamento no Mercado Pago: {e}')

    username = session.get('username', 'Jogador')
    return render_template('checkout_success.html', username=username)


@app.route('/checkout/pending')
def checkout_pending():
    return (
        '<h1>Pagamento em análise</h1>'
        '<p>Assim que o Mercado Pago confirmar, seu pedido será liberado automaticamente.</p>'
        '<a href="/">Voltar para o início</a>'
    )


@app.route('/checkout/failure')
def checkout_failure():
    external_reference = request.args.get('external_reference')
    if external_reference:
        purchase = database.get_purchase_by_id(external_reference)
        if purchase:
            database.update_purchase_status(purchase['id'], 'rejected')
    return (
        '<h1>Pagamento não concluído</h1>'
        '<p>Seu pagamento foi cancelado ou recusado. Nenhum valor foi cobrado.</p>'
        '<a href="/carrinho">Voltar ao carrinho</a>'
    )


@app.route('/webhook/mercadopago', methods=['POST'])
def mp_webhook():
    """Notificação assíncrona do Mercado Pago - fonte de verdade sobre o pagamento."""
    topic = request.args.get('type') or request.args.get('topic')
    data_id = request.args.get('data.id') or request.args.get('id')

    if sdk and topic == 'payment' and data_id:
        try:
            payment_info = sdk.payment().get(data_id).get('response', {})
            purchase_id = payment_info.get('external_reference')
            status = payment_info.get('status')
            if purchase_id:
                database.update_purchase_status(purchase_id, status, data_id)
        except Exception as e:
            print(f'Erro ao processar webhook do Mercado Pago: {e}')

    return jsonify({'received': True}), 200

if __name__ == '__main__':
    app.run(debug=True)