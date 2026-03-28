document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('image-modal');
  const modalImage = document.getElementById('modal-image');
  const modalCaption = document.getElementById('modal-caption');
  const closeModal = modal.querySelector('.close-modal');
  const backdrop = modal.querySelector('.image-modal-backdrop');

  const openModal = (src, alt) => {
    modalImage.src = src;
    modalImage.alt = alt || 'Expanded screenshot';
    modalCaption.textContent = alt || '';
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden';
  };

  const close = () => {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    modalImage.src = '';
    modalCaption.textContent = '';
    document.body.style.overflow = '';
  };

  document.querySelectorAll('.lightbox-image').forEach((img) => {
    img.addEventListener('click', () => {
      openModal(img.src, img.alt);
    });
  });

  closeModal.addEventListener('click', close);
  backdrop.addEventListener('click', close);

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.classList.contains('active')) {
      close();
    }
  });
});