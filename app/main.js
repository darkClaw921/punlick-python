// Функция отображения результатов из файла
function displayResults(data) {
    // Очищаем предыдущие результаты
    resultsTableBody.innerHTML = '';
    
    // Отображаем имя файла
    resultFilename.textContent = data.original_filename;
    
    // Добавляем элементы в таблицу
    data.items.forEach(item => {
        try {
            // Парсим JSON-строку текста элемента
            const itemData = JSON.parse(item.text);
            
            // Создаем новую строку таблицы
            const row = document.createElement('tr');
            
            // Добавляем класс для подсветки совпадений, если товар найден в векторной базе
            if (item.matched) {
                row.classList.add('table-success');
            }
            
            // Формируем содержимое ячеек
            const nameCell = document.createElement('td');
            nameCell.textContent = itemData.Наименование || '-';
            
            // Если есть процент совпадения, отображаем его в ячейке с названием
            if (itemData.Процент_совпадения) {
                const matchBadge = document.createElement('span');
                matchBadge.className = 'badge bg-success ms-2';
                matchBadge.textContent = `${itemData.Процент_совпадения}%`;
                nameCell.appendChild(matchBadge);
            }
            
            // Добавляем детали товара, если они есть
            if (itemData.Артикул || itemData.Категория) {
                const details = document.createElement('small');
                details.className = 'd-block text-muted';
                
                if (itemData.Артикул) {
                    details.textContent += `Артикул: ${itemData.Артикул}`;
                }
                
                if (itemData.Категория) {
                    if (details.textContent) details.textContent += ' | ';
                    details.textContent += `${itemData.Категория}`;
                    
                    if (itemData.Подкатегория) {
                        details.textContent += ` > ${itemData.Подкатегория}`;
                    }
                }
                
                nameCell.appendChild(details);
            }
            
            row.appendChild(nameCell);
            
            // Добавляем остальные ячейки
            const quantityCell = document.createElement('td');
            quantityCell.textContent = itemData.Количество || '-';
            row.appendChild(quantityCell);
            
            const unitCell = document.createElement('td');
            unitCell.textContent = itemData['Ед.изм.'] || '-';
            
            // Если есть цена, добавляем её к единице измерения
            if (itemData.Цена) {
                const priceSpan = document.createElement('span');
                priceSpan.className = 'd-block text-muted';
                priceSpan.textContent = `${itemData.Цена} ${itemData.Валюта || 'RUB'}`;
                unitCell.appendChild(priceSpan);
            }
            
            row.appendChild(unitCell);
            
            // Добавляем строку в таблицу
            resultsTableBody.appendChild(row);
        } catch (e) {
            console.warn('Could not parse item:', item.text, e);
        }
    });
    
    // Если нет результатов, добавляем пустую строку
    if (data.items.length === 0) {
        resultsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">Нет результатов</td></tr>';
    }
    
    // Показываем карточку с результатами
    resultsCard.classList.remove('d-none');
}

// Функция отображения результатов из чата
function displayChatResults(data) {
    // Очищаем предыдущие результаты
    chatResultsTableBody.innerHTML = '';
    
    // Добавляем элементы в таблицу
    data.items.forEach(item => {
        try {
            // Парсим JSON-строку текста элемента
            const itemData = JSON.parse(item.text);
            
            // Создаем новую строку таблицы
            const row = document.createElement('tr');
            
            // Добавляем класс для подсветки совпадений, если товар найден в векторной базе
            if (item.matched) {
                row.classList.add('table-success');
            }
            
            // Формируем содержимое ячеек
            const nameCell = document.createElement('td');
            nameCell.textContent = itemData.Наименование || '-';
            
            // Если есть процент совпадения, отображаем его в ячейке с названием
            if (itemData.Процент_совпадения) {
                const matchBadge = document.createElement('span');
                matchBadge.className = 'badge bg-success ms-2';
                matchBadge.textContent = `${itemData.Процент_совпадения}%`;
                nameCell.appendChild(matchBadge);
            }
            
            // Добавляем детали товара, если они есть
            if (itemData.Артикул || itemData.Категория) {
                const details = document.createElement('small');
                details.className = 'd-block text-muted';
                
                if (itemData.Артикул) {
                    details.textContent += `Артикул: ${itemData.Артикул}`;
                }
                
                if (itemData.Категория) {
                    if (details.textContent) details.textContent += ' | ';
                    details.textContent += `${itemData.Категория}`;
                    
                    if (itemData.Подкатегория) {
                        details.textContent += ` > ${itemData.Подкатегория}`;
                    }
                }
                
                nameCell.appendChild(details);
            }
            
            row.appendChild(nameCell);
            
            // Добавляем остальные ячейки
            const quantityCell = document.createElement('td');
            quantityCell.textContent = itemData.Количество || '-';
            row.appendChild(quantityCell);
            
            const unitCell = document.createElement('td');
            unitCell.textContent = itemData['Ед.изм.'] || '-';
            
            // Если есть цена, добавляем её к единице измерения
            if (itemData.Цена) {
                const priceSpan = document.createElement('span');
                priceSpan.className = 'd-block text-muted';
                priceSpan.textContent = `${itemData.Цена} ${itemData.Валюта || 'RUB'}`;
                unitCell.appendChild(priceSpan);
            }
            
            row.appendChild(unitCell);
            
            // Добавляем строку в таблицу
            chatResultsTableBody.appendChild(row);
        } catch (e) {
            console.warn('Could not parse item:', item.text, e);
        }
    });
    
    // Если нет результатов, добавляем пустую строку
    if (data.items.length === 0) {
        chatResultsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">Нет результатов</td></tr>';
    }
    
    // Показываем карточку с результатами
    chatResultsCard.classList.remove('d-none');
} 