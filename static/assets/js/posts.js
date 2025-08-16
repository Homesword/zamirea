    let offset = 0;
    const limit = 5;
    let loading = false;
    let allLoaded = false;

    async function loadMorePosts() {
    if (loading || allLoaded) return;
    loading = true;
    document.getElementById('loader').style.display = 'block';

    try {
        let url = `/profile/load-posts?offset=${offset}&limit=${limit}`;
        if (typeof userId !== 'undefined' && userId !== null) {
            url += `&user_id=${userId}`;
        }

        const response = await fetch(url);
        const data = await response.json();

        if (offset === 0 && data.posts.length === 0) {
            const messageBox = document.getElementById('no-posts-message');
            if (messageBox) {
                messageBox.style.display = 'block';
            }
            document.getElementById('loader').style.display = 'none';
            allLoaded = true;
            return;
        }

        if (data.posts.length === 0) {
            allLoaded = true;
            document.getElementById('loader').innerText = 'Больше постов нет';
            return;
        }

        for (const post of data.posts) {
            const postHtml = createPostHtml(post);
            document.getElementById('posts-container').insertAdjacentHTML('beforeend', postHtml);
        }

        offset += data.posts.length;
    } catch (error) {
        console.error('Ошибка загрузки постов:', error);
    } finally {
        loading = false;
        document.getElementById('loader').style.display = 'none';
    }
}


    function createPostHtml(post) {
        return `
    <div class="news-feed news-feed-post" id="${post.post_id}">
        <div class="post-header d-flex justify-content-between align-items-center">
            <div class="image">
                <a href="/profile/${post.who}">
                    <img src="${post.avatar}" class="rounded-circle" alt="avatar">
                </a>
            </div>
            <div class="info ms-3">
                <span class="name"><a href="/profile/${post.who}">${post.name}</a></span>
                <span class="small-text"><a href="mailto:${post.login}">${post.login}</a></span>
            </div>
            ${post.is_owner ? `
            <div class="dropdown">
                <button class="dropdown-toggle" type="button" data-bs-toggle="dropdown">
                    <i class="flaticon-menu"></i></button>
                <ul class="dropdown-menu">
                    <li><a class="dropdown-item d-flex align-items-center" href="#" name="edit-button">
                        <i class="flaticon-edit"></i> Редактировать пост</a></li>
                    <li><a class="dropdown-item d-flex align-items-center" href="#" name="delete-button">
                        <i class="flaticon-trash"></i> Удалить пост</a></li>
                </ul>
            </div>` : ''}
        </div>
        <div class="post-body">
            <p>${post.text.replace(/\n/g, '<br>')}</p>
            <ul class="post-meta-wrap d-flex justify-content-between align-items-center">
                <li class="post-react">
                    <form id="likeForm-${post.post_id}"
                        action="/profile/like-post" method="POST">
                        <input type="hidden" name="post_id" value="${post.post_id}">
                        <input type="hidden" name="csrf_token" value="${csrfToken}">
                        <a href="#" class="like-button"
                            data-form-id="likeForm-${post.post_id}">
                            <i class="flaticon-like"></i>
                                        <span ${post.liked_by_viewer ? 'style="color: #3644D9;"' : ''}>Лайков</span>
            <span class="number" ${post.liked_by_viewer ? 'style="color: #3644D9;"' : ''}>
                ${post.likes}</span>
                        </a>
                    </form>
          

                <li class="post-share">
                    <a href="#" onclick="return false;"><i class="flaticon-calendar"></i>
                        <span>Дата публикации</span> <span class="number">${post.timestamp}</span></a>
                </li>
            </ul>
        </div>
    </div>`;
    }


    window.addEventListener('scroll', () => {
        const scrollBottom = window.innerHeight + window.scrollY >= document.body.offsetHeight - 300;
        if (scrollBottom) {
            loadMorePosts();
        }
    });

    document.addEventListener('DOMContentLoaded', () => {
        loadMorePosts();
    });