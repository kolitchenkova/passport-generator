document.addEventListener('DOMContentLoaded', () => {
    const productSelect = document.getElementById('product-select');
    const templateSelect = document.getElementById('template-select');
    const categoryFilter = document.getElementById('category-filter');
    const generateForm = document.getElementById('generate-form');
    const submitBtn = document.getElementById('submit-btn');
    const productsTbody = document.getElementById('products-tbody');

    const resultCard = document.getElementById('result-card');
    const resultTitle = document.getElementById('result-title');
    const resultBadge = document.getElementById('result-badge');
    const resultBody = document.getElementById('result-body');
    const resultActions = document.getElementById('result-actions');
    const downloadLink = document.getElementById('download-link');

    // Загрузка всех начальных данных
    loadCategories();
    loadTemplates();
    loadProducts();
    loadAnalytics();

    // 1. Загрузка категорий
    async function loadCategories() {
        try {
            const res = await fetch('/api/v1/categories');
            const categories = await res.json();
            categories.forEach(cat => {
                const opt = document.createElement('option');
                opt.value = cat.id;
                opt.textContent = cat.name;
                categoryFilter.appendChild(opt);
            });
        } catch (e) {
            console.error('Ошибка загрузки категорий:', e);
        }
    }

    // 2. Загрузка шаблонов
    async function loadTemplates() {
        try {
            const res = await fetch('/api/v1/templates');
            const templates = await res.json();
            templateSelect.innerHTML = '<option value="">-- Выберите шаблон оформления --</option>';
            templates.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t.id;
                opt.textContent = `${t.name} (${t.required_parameter_codes.join(', ') || 'без ограничений'})`;
                templateSelect.appendChild(opt);
            });
        } catch (e) {
            console.error('Ошибка загрузки шаблонов:', e);
        }
    }

    // 3. Загрузка изделий
    async function loadProducts(categoryId = null) {
        try {
            let url = '/api/v1/products?limit=50';
            if (categoryId) {
                url += `&category_id=${categoryId}`;
            }
            const res = await fetch(url);
            const products = await res.json();

            // Заполняем выпадающий список
            productSelect.innerHTML = '<option value="">-- Выберите изделие --</option>';
            products.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `[${p.sku}] ${p.name}`;
                productSelect.appendChild(opt);
            });

            // Заполняем таблицу каталога
            productsTbody.innerHTML = '';
            if (products.length === 0) {
                productsTbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">Нет изделий в категории</td></tr>';
                return;
            }

            products.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${p.id}</td>
                    <td><strong>${p.sku}</strong></td>
                    <td>${p.name}</td>
                    <td>
                        <button class="btn btn-outline select-product-btn" data-id="${p.id}">
                            Выбрать
                        </button>
                    </td>
                `;
                productsTbody.appendChild(tr);
            });

            // Кнопки быстрого выбора изделия из таблицы
            document.querySelectorAll('.select-product-btn').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const id = e.target.getAttribute('data-id');
                    productSelect.value = id;
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                });
            });

        } catch (e) {
            console.error('Ошибка загрузки изделий:', e);
        }
    }

    // 4. Загрузка сводки аналитики
    async function loadAnalytics() {
        try {
            const res = await fetch('/api/v1/analytics/overview');
            if (res.ok) {
                const data = await res.json();
                document.getElementById('stat-total').textContent = data.total_generations;
                document.getElementById('stat-success').textContent = data.success_count;
                document.getElementById('stat-failed').textContent = data.failed_count;
                document.getElementById('stat-rate').textContent = `${data.success_rate_percent}%`;
            }
        } catch (e) {
            console.error('Ошибка аналитики:', e);
        }
    }

    // Фильтр по категории
    categoryFilter.addEventListener('change', (e) => {
        loadProducts(e.target.value);
    });

    // 5. Обработка отправки формы генерации паспорта
    generateForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const productId = parseInt(productSelect.value);
        const templateId = parseInt(templateSelect.value);

        if (!productId || !templateId) {
            alert('Пожалуйста, выберите изделие и шаблон');
            return;
        }

        submitBtn.disabled = true;
        submitBtn.querySelector('.btn-text').textContent = 'Генерация DOCX...';
        resultCard.classList.add('hidden');

        try {
            const response = await fetch('/api/v1/passports/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ product_id: productId, template_id: templateId }),
            });

            const data = await response.json();
            resultCard.classList.remove('hidden');

            if (response.status === 200) {
                // УСПЕХ (или кэширование)
                resultCard.className = 'card result-card';
                resultActions.classList.remove('hidden');
                downloadLink.href = data.download_url;

                if (data.reused) {
                    // Бизнес-правило 2: Дедупликация
                    resultCard.classList.add('card-warning');
                    resultTitle.textContent = 'Документ возвращен из кэша (10 мин)';
                    resultBadge.className = 'badge badge-warning';
                    resultBadge.textContent = 'Кэш (reused: true)';
                } else {
                    // Новая генерация
                    resultTitle.textContent = 'Паспорт успешно сгенерирован!';
                    resultBadge.className = 'badge badge-success';
                    resultBadge.textContent = 'Успешно';
                }

                resultBody.innerHTML = `
                    <p><strong>Файл:</strong> <code>${data.output_filename}</code></p>
                    <p class="text-muted" style="margin-top: 6px;">${data.message}</p>
                `;
            } else if (response.status === 422) {
                // БИЗНЕС-ПРАВИЛО 1: Отказ из-за отсутствия обязательных параметров
                resultCard.className = 'card result-card card-error';
                resultTitle.textContent = 'Отказ формирования документа (422)';
                resultBadge.className = 'badge badge-danger';
                resultBadge.textContent = 'Неполные данные';
                resultActions.classList.add('hidden');

                const missing = data.detail.missing_parameters || [];
                resultBody.innerHTML = `
                    <p><strong>${data.detail.message}</strong></p>
                    <p style="margin-top: 6px;">У данного изделия в каталоге не заполнены обязательные характеристики:</p>
                    <ul class="missing-params-list">
                        ${missing.map(p => `<li><code>${p}</code></li>`).join('')}
                    </ul>
                `;
            } else {
                // Другие ошибки
                resultCard.className = 'card result-card card-error';
                resultTitle.textContent = 'Ошибка сервера';
                resultBadge.className = 'badge badge-danger';
                resultBadge.textContent = `Код ${response.status}`;
                resultActions.classList.add('hidden');
                resultBody.innerHTML = `<p>${data.detail || 'Непредвиденная ошибка при генерации'}</p>`;
            }

            // Обновляем счетчики аналитики
            loadAnalytics();

        } catch (err) {
            console.error('Ошибка запроса:', err);
            alert('Сетевая ошибка при обращении к серверу');
        } finally {
            submitBtn.disabled = false;
            submitBtn.querySelector('.btn-text').textContent = 'Сгенерировать документ';
        }
    });
});