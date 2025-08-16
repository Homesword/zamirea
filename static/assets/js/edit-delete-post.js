
// алгоритм редактирования поста
                            document.addEventListener('DOMContentLoaded', function () {
                                document.querySelectorAll('a[name="edit-button"]').forEach(function (editBtn) {
                                    editBtn.addEventListener('click', function (e) {
                                        e.preventDefault();


                                        const postElement = editBtn.closest('.news-feed-post');
                                        const postId = postElement.id
                                        const postBody = postElement.querySelector('.post-body');
                                        const postContent = postBody.querySelector('p');
                                        const postMeta = postBody.querySelector('.post-meta-wrap');
                                            
                                        if (!postContent || !postMeta) return;

                                        // чтобы не дублировать форму
                                        if (postBody.querySelector('form.edit-post-form')) return;

                                        const originalText = postContent.innerText.trim();

                                        postContent.style.display = 'none';
                                        postMeta.style.display = 'none';

                                        const form = document.createElement('form');
                                        form.className = 'edit-post-form';
                                        form.method = 'POST';
                                        form.action = '/post/edit-post';

                                        const textarea = document.createElement('textarea');
                                        textarea.name = 'edited_text';
                                        textarea.className = 'form-control';
                                        textarea.required = true;
                                        textarea.style = 'width: 100%; min-height: 120px; max-height: 500px';
                                        textarea.maxLength = 300;
                                        textarea.value = originalText;
                                        form.appendChild(textarea);

                                        const hiddenInput = document.createElement('input');
                                        hiddenInput.type = 'hidden';
                                        hiddenInput.name = 'post_id';
                                        hiddenInput.value = postId;
                                        form.appendChild(hiddenInput);

                                        const csrfInput = document.createElement('input');
                                        csrfInput.type = 'hidden';
                                        csrfInput.name = 'csrf_token';
                                        csrfInput.value = csrfToken; 
                                        form.appendChild(csrfInput);

                                        const buttonWrapper = document.createElement('div');
                                        buttonWrapper.style.marginTop = '10px';
                                        buttonWrapper.className = 'd-flex gap-2';

                                        // кнопка сохранить
                                        const submitBtn = document.createElement('button');
                                        submitBtn.type = 'submit';
                                        submitBtn.className = 'btn btn-primary';
                                        submitBtn.textContent = 'Сохранить';

                                        // кнопка отмена
                                        const cancelBtn = document.createElement('button');
                                        cancelBtn.type = 'button';
                                        cancelBtn.className = 'btn btn-secondary';
                                        cancelBtn.textContent = 'Отмена';

                                        cancelBtn.addEventListener('click', function () {
                                            form.remove();
                                            postContent.style.display = '';
                                            postMeta.style.display = '';
                                        });

                                        buttonWrapper.appendChild(submitBtn);
                                        buttonWrapper.appendChild(cancelBtn);
                                        form.appendChild(buttonWrapper);

                                        postBody.appendChild(form);
                                    });
                                });
                            });
    
document.addEventListener('DOMContentLoaded', function () {
                                const deleteButtons = document.querySelectorAll('a[name="delete-button"]');

                                deleteButtons.forEach(function (deleteBtn) {
                                    if (deleteBtn.dataset.bound === "true") return;
                                    deleteBtn.dataset.bound = "true";

                                    deleteBtn.addEventListener('click', function (e) {
                                        e.preventDefault();

                                        const confirmed = confirm("Вы действительно хотите удалить этот пост?");
                                        if (!confirmed) return;

                                        const postElement = deleteBtn.closest('.news-feed-post');
                                        if (!postElement) return;

                                        const postId = postElement.id.replace('post-', '');

                                        const form = document.createElement('form');
                                        form.method = 'POST';
                                        form.action = '/profile/delete-post';

                                        const input = document.createElement('input');
                                        input.type = 'hidden';
                                        input.name = 'post_id';
                                        input.value = postId;
                                        form.appendChild(input);
                                        
                                        const csrfInput = document.createElement('input');
                                        csrfInput.type = 'hidden';
                                        csrfInput.name = 'csrf_token';
                                        csrfInput.value = csrfToken; 
                                        form.appendChild(csrfInput);

                                        document.body.appendChild(form);
                                        form.submit();
                                    });
                                });
                            });