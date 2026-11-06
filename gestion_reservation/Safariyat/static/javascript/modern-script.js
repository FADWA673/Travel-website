document.addEventListener('DOMContentLoaded', function() {
    const elements = document.querySelectorAll('.animate-on-scroll');
    // Vérifiez si des éléments ont été trouvés
    if (!elements || elements.length === 0) {
        console.log('Aucun élément avec la classe .animate-on-scroll n\'a été trouvé.');
        return; // Arrête l'exécution de la fonction si aucun élément n'est trouvé
    }
    const checkElementsInViewport = () => {
        for (let i = 0; i < elements.length; i++) {
            const element = elements[i];
            // Vérifiez si l'élément existe avant de continuer
            if (element) {
                const elementPosition = element.getBoundingClientRect().top;
                const windowHeight = window.innerHeight;
                const elementVisible = 150; // Adjust as needed
                if (elementPosition < windowHeight - elementVisible) {
                    element.classList.add('visible');
                    const animationClass = element.dataset.animation;
                    const delay = element.dataset.delay;
                    if (animationClass) {
                        element.classList.add(animationClass);
                    }
                    if (delay) {
                        element.style.animationDelay = delay;
                    }
                } else {
                    element.classList.remove('visible');
                    const animationClass = element.dataset.animation;
                    if (animationClass) {
                        element.classList.remove(animationClass);
                    }
                }
            }
        }
    };
    // Initial check on page load
    checkElementsInViewport();
    // Check on scroll and resize
    window.addEventListener('scroll', checkElementsInViewport);
    window.addEventListener('resize', checkElementsInViewport);
});