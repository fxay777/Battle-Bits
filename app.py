from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'batlle-bits-super-secret-key-2024-change-in-prod'

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/vips')
def vips():
    return render_template('vips.html')

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
        
        # Validações
        if not usuario or len(usuario) < 3:
            erro = 'Nome de usuário deve ter no mínimo 3 caracteres'
        elif not email or '@' not in email:
            erro = 'Email inválido'
        elif len(senha) < 6:
            erro = 'Senha deve ter no mínimo 6 caracteres'
        elif senha != confirmar_senha:
            erro = 'As senhas não correspondem'
        else:
            sucesso = f'Conta criada com sucesso, {usuario}! Você pode fazer login agora.'
    
    return render_template('cadastro.html', erro=erro, sucesso=sucesso)

@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        senha = request.form.get('senha', '')
        
        # Validação simples (você pode expandir isso com banco de dados depois)
        if not usuario or not senha:
            erro = 'Usuário e senha são obrigatórios'
        elif usuario == 'admin' and senha == '123':
            session['admin'] = True
            session['username'] = usuario
            return redirect(url_for('forum'))
        else:
            erro = 'Usuário ou senha inválidos'
    
    return render_template('login.html', erro=erro)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('forum'))

if __name__ == '__main__':
    app.run(debug=True)
