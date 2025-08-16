window.PROFILE_PAGE = window.PROFILE_PAGE || {};
const tabLoaders = {};

function renderPost(post, index) {
  const text = post?.text ? String(post.text).replace(/\n/g, "<br>") : "";
  const avatar = post?.avatar || "/static/assets/images/my-profile.jpg";
  const name = post?.name || "User";
  const login = post?.login || "";
  const likes = post?.likes ?? 0;
  const liked = post?.liked_by_viewer;
  const csrf = window.PROFILE_PAGE.csrfToken || "";

  return `
    <div class="news-feed news-feed-post" id="${post.post_id}">
      <div class="post-header d-flex justify-content-between align-items-center">
        <div class="image">
          <a href="/profile/${post.who}">
            <img src="${avatar}" style="width: 55px; height: 55px" class="rounded-circle" alt="avatar">
          </a>
        </div>
        <div class="info ms-3">
          <span class="name"><a href="/profile/${post.who}">${name}</a></span>
          <span class="small-text"><a href="mailto:${login}">${login}</a></span>
        </div>
      </div>
      <div class="post-body">
        <p>${text}</p>
        <ul class="post-meta-wrap d-flex justify-content-between align-items-center">
          <form id="likeForm-${index}" action="/profile/like-post" method="POST">
            <li class="post-react">
              <input type="hidden" name="post_id" value="${post.post_id}">
              <input type="hidden" name="csrf_token" value="${csrf}">
              <a href="#" class="like-button" data-form-id="likeForm-${index}">
                <i class="flaticon-like"></i>
                <span ${liked ? 'style="color: #3644D9;"' : ''}>Лайков</span>
                <span class="number" ${liked ? 'style="color: #3644D9;"' : ''}>${likes}</span>
              </a>
            </li>
          </form>
          <li class="post-share">
            <a href="#" onclick="return false;">
              <i class="flaticon-calendar"></i>
              <span>Дата публикации</span>
              <span class="number">${post.timestamp || ''}</span>
            </a>
          </li>
        </ul>
      </div>
    </div>`.trim();
}

function setupLoaderForTab(tabId, url) {
  const tabContainer = document.getElementById(tabId);
  if (!tabContainer) return;

  const area = tabContainer.querySelector('.news-feed-area');
  if (!area) return;

  let loader = tabContainer.querySelector('#loader');
  if (!loader) {
    loader = document.createElement('div');
    loader.id = 'loader';
    loader.className = 'load-more-posts-btn';
    loader.innerHTML = '<a href="#" onclick="return false;"><i class="flaticon-loading"></i> Загрузка...</a>';
    area.appendChild(loader);
  }

  let offset = 0;
  const limit = 5;
  let loading = false;
  let allLoaded = false;

  const loadMore = async () => {
    if (loading || allLoaded) return;
    loading = true;
    loader.style.display = "block";

    try {
      const uid = window.PROFILE_PAGE.userId || 'null';
      const resp = await fetch(`${url}?offset=${offset}&limit=${limit}&user_id=${uid}`);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();
      const posts = data.posts || [];

      if (!Array.isArray(posts) || posts.length === 0) {
        allLoaded = true;
        loader.innerHTML = "<span>Больше нет контента :c</span>";
        return;
      }

      let added = 0;
      posts.forEach((post, idx) => {
        if (area.querySelector(`[id="${String(post.post_id)}"]`)) return;
        const html = renderPost(post, offset + idx);
        const temp = document.createElement('div');
        temp.innerHTML = html;
        const el = temp.firstElementChild;
        if (el) {
          area.insertBefore(el, loader);
          added++;
        }
      });

      offset += posts.length;

      if (posts.length < limit || added === 0) {
        allLoaded = true;
        loader.innerHTML = "<span>Больше нет контента :c</span>";
      }
    } catch (err) {
      console.error("Ошибка подгрузки в табе:", tabId, err);
      loader.innerHTML = "<span>Ошибка загрузки, попробуйте позже</span>";
    } finally {
      if (!allLoaded) loader.style.display = "none";
      loading = false;
    }
  };

  const init = () => {
    window.addEventListener('scroll', () => {
      const isActive = tabContainer.classList.contains('active') || tabContainer.classList.contains('show');
      if (!isActive || loading || allLoaded) return;
      if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 400) {
        loadMore();
      }
    });

    loadMore();
    tabLoaders[tabId] = { init, initialized: true };
  };

  tabLoaders[tabId] = { init, initialized: false };
}

document.addEventListener("DOMContentLoaded", () => {
  setupLoaderForTab('posts', '/profile/load-posts');
  setupLoaderForTab('likes', '/profile/load-likes');

  ['posts', 'likes'].forEach(tabId => {
    const tab = document.getElementById(tabId);
    if (tab && (tab.classList.contains("active") || tab.classList.contains("show"))) {
      if (tabLoaders[tabId] && !tabLoaders[tabId].initialized) {
        tabLoaders[tabId].init();
      }
    }
  });

  document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
    tab.addEventListener('shown.bs.tab', (event) => {
      const targetTab = event.target.getAttribute('href').substring(1);
      if (tabLoaders[targetTab] && !tabLoaders[targetTab].initialized) {
        tabLoaders[targetTab].init();
      }
    });
  });
});

function renderSub(user) {
  return `
    <div class="col-lg-3 col-sm-6 mb-4" id="sub-${user.id}">
      <div class="single-friends-card">
        <div class="friends-image position-relative">
          <a href="/profile/${user.id}">
            <img src="/static/assets/images/friends-bg.jpg" alt="background" class="w-100 rounded">
          </a>
          <div class="icon position-absolute top-50 start-50 translate-middle">
            <a href="/profile/${user.id}"><i class="flaticon-user"></i></a>
          </div>
        </div>
        <div class="friends-content p-3">
          <div class="friends-info d-flex align-items-center mb-2">
            <a href="/messages/${user.id}">
              <img src="${user.avatar || '/static/assets/images/my-profile.jpg'}" alt="avatar_sub" style="width:50px; height:50px;" class="rounded-circle">
            </a>
            <div class="text ms-3">
              <h5 class="mb-1"><a href="/profile/${user.id}">${user.name || 'User'}</a></h5>
              <small>${user.login || ''}</small>
            </div>
          </div>
          <ul class="statistics d-flex justify-content-between mb-3">
            <li><span class="item-number">${user.subscriptions || 0}</span><span class="item-text">Подписок</span></li>
            <li><span class="item-number">${user.followers || 0}</span><span class="item-text">Подписчиков</span></li>
          </ul>
        </div>
      </div>
    </div>`;
}

function setupSubLoader() {
  const subTab = document.getElementById("sub");
  if (!subTab) return;

  const area = subTab.querySelector(".news-feed-area") || subTab.querySelector(".row.news-feed-area");
  if (!area) return;

  let loader = subTab.querySelector("#loader-sub");
  if (!loader) {
    loader = document.createElement("div");
    loader.id = "loader-sub";
    loader.className = "load-more-posts-btn";
    loader.innerHTML = '<a href="#" onclick="return false;"><i class="flaticon-loading"></i> Загрузка...</a>';
    area.appendChild(loader);
  }

  let offset = 0;
  const limit = 5;
  let loading = false;
  let allLoaded = false;

  async function loadMoreSubs() {
    if (loading || allLoaded) return;
    loading = true;
    loader.style.display = "block";

    try {
      const uid = window.PROFILE_PAGE.userId || 'null';
      const resp = await fetch(`/subscriptions/load-sub?offset=${offset}&limit=${limit}&user_id=${uid}`);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
      const subs = data.subs || [];

      if (!Array.isArray(subs) || subs.length === 0) {
        allLoaded = true;
        loader.innerHTML = "<span>Больше нет контента :c</span>";
        return;
      }

      let added = 0;
      subs.forEach((user) => {
        if (document.getElementById(`sub-${user.id}`)) return;
        const html = renderSub(user);
        const temp = document.createElement("div");
        temp.innerHTML = html.trim();
        const el = temp.firstElementChild;
        if (el) {
          area.insertBefore(el, loader);
          added++;
        }
      });

      offset += subs.length;

      if (subs.length < limit || added === 0) {
        allLoaded = true;
        loader.innerHTML = "<span>Больше нет подписок</span>";
      }
    } catch (err) {
      console.error("Ошибка загрузки подписок:", err);
      loader.innerHTML = "<span>Ошибка загрузки, попробуйте позже</span>";
    } finally {
      loader.style.display = allLoaded ? "none" : "block";
      loading = false;
    }
  }

  window.addEventListener("scroll", () => {
    const isActive = subTab.classList.contains("show") || subTab.classList.contains("active");
    if (!isActive || allLoaded) return;
    if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 400) {
      loadMoreSubs();
    }
  });

  document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(tab => {
    tab.addEventListener('shown.bs.tab', (e) => {
      if (e.target.getAttribute("href") === "#sub" && offset === 0) {
        loadMoreSubs();
      }
    });
  });

  if (subTab.classList.contains("show") || subTab.classList.contains("active")) {
    loadMoreSubs();
  }
}

document.addEventListener("DOMContentLoaded", setupSubLoader);
