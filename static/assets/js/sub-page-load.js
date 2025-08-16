(function () {
  'use strict';

  function renderFriendCard(user, tabPrefix) {
    const safePrefix = String(tabPrefix).replace(/[^a-z0-9_-]/ig, '');
    return `
      <div class="col-lg-3 col-sm-6 mb-4" id="friend-${safePrefix}-${user.id}">
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
                <img src="${user.avatar || '/static/assets/images/my-profile.jpg'}" alt="avatar_sub" class="rounded-circle" style="width:50px; height:50px;">
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

  function setupFriendsLoader(tabPaneId, apiUrl) {
    const tab = document.getElementById(tabPaneId);
    if (!tab) return;

    const area = tab.querySelector('.friends-list-row') || tab.querySelector('.row') || tab;
    if (!area) return;

    let loader = area.querySelector('.load-more-posts-btn');
    if (!loader) {
      loader = document.createElement('div');
      loader.className = 'load-more-posts-btn text-center w-100 mt-3';
      loader.innerHTML = '<a href="#" onclick="return false;"><i class="flaticon-loading"></i> Загрузка...</a>';
      area.appendChild(loader);
    }

    let offset = 0;
    const limit = 8;
    let loading = false;
    let allLoaded = false;

    async function loadMore() {
      if (loading || allLoaded) return;
      loading = true;
      loader.style.display = 'block';

      try {
        const resp = await fetch(`${apiUrl}?offset=${offset}&limit=${limit}&user_id=${rowid}`);
        if (!resp.ok) throw new Error('HTTP ' + resp.status);
        const data = await resp.json();
        const items = data.subs || [];

        if (!Array.isArray(items) || items.length === 0) {
          allLoaded = true;
          loader.innerHTML = '<span>Больше нет контента :c</span>';
          return;
        }

        let added = 0;
        const safePrefix = String(tabPaneId).replace(/[^a-z0-9_-]/ig, '');

        items.forEach(user => {
          if (!user || typeof user.id === 'undefined') return;
          if (area.querySelector(`#friend-${safePrefix}-${user.id}`)) return;
          const frag = document.createRange().createContextualFragment(renderFriendCard(user, safePrefix));
          area.insertBefore(frag, loader);
          added++;
        });

        offset += items.length;

        if (items.length < limit || added === 0) {
          allLoaded = true;
          loader.innerHTML = '<span>Больше нет контента :c</span>';
        }
      } catch (err) {
        console.error('Ошибка загрузки списка:', err);
        loader.innerHTML = '<span>Ошибка загрузки</span>';
      } finally {
        loading = false;
        if (allLoaded) loader.style.display = 'none';
      }
    }

    window.addEventListener('scroll', () => {
      const isActive = tab.classList.contains('active') || tab.classList.contains('show');
      if (!isActive || allLoaded) return;
      if ((window.innerHeight + window.scrollY) >= document.body.offsetHeight - 400) {
        loadMore();
      }
    });

    document.querySelectorAll('a[data-bs-toggle="tab"]').forEach(t => {
      t.addEventListener('shown.bs.tab', (e) => {
        const href = e.target.getAttribute('href');
        if (href === `#${tabPaneId}` && offset === 0) loadMore();
      });
    });

    if (tab.classList.contains('active') || tab.classList.contains('show')) {
      loadMore();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    setupFriendsLoader('sub-block', '/subscriptions/load-sub');
    setupFriendsLoader('followers-block', '/subscriptions/load-followers');
  });

})();
