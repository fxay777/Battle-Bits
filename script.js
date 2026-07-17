// Aguarda o carregamento total do DOM
document.addEventListener('DOMContentLoaded', () => {
    
    // Seleção de Elementos da Navbar Mobile
    const hamburger = document.querySelector('.hamburger');
    const navMenu = document.querySelector('.nav-menu');

    if (hamburger && navMenu) {
        // Alterna classe active ao clicar no menu hamburguer
        hamburger.addEventListener('click', () => {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('active');
        });

        // Fecha o menu mobile se o usuário clicar em qualquer link interno
        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                hamburger.classList.remove('active');
                navMenu.classList.remove('active');
            });
        });
    }

    // Gerenciador de scroll para opacidade da navbar (Opcional)
    window.addEventListener('scroll', () => {
        const navbar = document.querySelector('.navbar');
        if (navbar) {
            if (window.scrollY > 50) {
                navbar.style.backgroundColor = '#020104'; // Fica discretamente mais escuro ao rolar
            } else {
                navbar.style.backgroundColor = '#07060a'; // Volta ao padrão
            }
        }
    });

});