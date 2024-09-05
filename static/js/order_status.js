document.addEventListener("DOMContentLoaded", () => {
    const socket = io('http://43.201.92.62:8000', {
        transports: ['websocket']
    });

    const ownerid = localStorage.getItem('ownerid');
    if (!ownerid) {
        alert("�߸��� �����Դϴ�. �ٽ� �α��� ���ּ���.");
        window.location.href = '/';
    }

    socket.on('connect', () => {
        console.log(`Connected to WebSocket: ${socket.id}`);
        socket.emit('join', { ownerid });
    });

    socket.on('disconnect', () => {
        console.log('Disconnected from WebSocket');
    });

    socket.on('order_list', (response) => {
        const sortedOrders = response.sort((a, b) => new Date(b.ordertime) - new Date(a.ordertime));
        renderOrders(sortedOrders);
    });

    socket.on('new_order', (newOrder) => {
        console.log('New order received:', newOrder);
        addNewOrder(newOrder);
    });

    socket.emit('get_orders', { ownerid });

    function goBack() {
        localStorage.setItem('ownerid', ownerid);
        window.location.href = '/Main';
    }

    function openOrderDetail(order) {
        document.getElementById('detail-tablenumber').textContent = `���̺� ��ȣ : ${order.tablenumber}`;
        document.getElementById('detail-ordertime').textContent = `�ֹ��ð� : ${formatTime(order.ordertime)}`;
        document.getElementById('detail-info-container').innerHTML = order.order_details.map((detail, idx) => `
            <div class="detail-item" key=${idx}>
                <span class="detail-menu-name">${detail.menu_name}</span>
                <span class="detail-menu-quantity">${detail.quantity}</span>
                <span class="detail-menu-price">${formatPrice(parseFloat(detail.menu_price) * parseInt(detail.quantity))}</span>
            </div>
        `).join('');
        document.getElementById('price-sum').textContent = formatPrice(order.order_details.reduce((total, item) => total + (parseFloat(item.menu_price) * parseInt(item.quantity)), 0));
        document.getElementById('order-detail-frame').style.display = 'block';
        document.getElementById('order-detail-frame').dataset.orderid = order.orderid;
    }

    function closeOrderDetail() {
        document.getElementById('order-detail-frame').style.display = 'none';
        document.getElementById('order-detail-frame').dataset.orderid = '';
    }

    async function handleServeDone() {
        const orderid = document.getElementById('order-detail-frame').dataset.orderid;
        try {
            const response = await fetch('http://43.201.92.62/order/serve_done', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ orderid })
            });
            const result = await response.json();
            if (result.message) {
                removeOrder(orderid);
                closeOrderDetail();
            } else {
                alert("���� �Ϸ� ó�� �� ������ �߻��߽��ϴ�.");
            }
        } catch (error) {
            console.error("���� �Ϸ� ó�� �� ������ �߻��߽��ϴ�!", error);
            alert("���� �Ϸ� ó�� �� ������ �߻��߽��ϴ�.");
        }
    }

    function formatPrice(price) {
        return Number(price).toLocaleString('ko-KR') + '\';
    }

    function formatTime(timeString) {
        if (timeString && typeof timeString === 'string') {
            const parts = timeString.split('T');
            if (parts.length > 1) {
                const timeParts = parts[1].split('.');
                if (timeParts.length > 0) {
                    return timeParts[0];
                }
            }
        }
        return '';
    }

    function renderOrders(orders) {
        const orderList = document.getElementById('order-list');
        orderList.innerHTML = orders.map((order) => `
            <div class="order-item" key=${order.orderid} onclick="openOrderDetail(${order})">
                <div class="order-info">
                    <div class="order-detail">${formatTime(order.ordertime)}</div>
                    <div class="order-detail">${order.tablenumber}</div>
                    <div class="order-detail">${order.order_details.map((detail) => detail.menu_name).join(', ')}</div>
                    <div class="order-detail">${order.order_details.map((detail) => detail.quantity).join(', ')}</div>
                    <div class="order-detail">${order.pg}</div>
                    <div class="order-detail">${order.order_details.map((detail) => formatPrice(parseFloat(detail.menu_price) * parseInt(detail.quantity))).join(', ')}</div>
                </div>
            </div>
        `).join('');
        document.getElementById('order-count').textContent = `���� �ֹ� �Ǽ� : ${orders.length}��`;
    }

    function addNewOrder(order) {
        const orderList = document.getElementById('order-list');
        const newOrderHtml = `
            <div class="order-item" key=${order.orderid} onclick="openOrderDetail(${order})">
                <div class="order-info">
                    <div class="order-detail">${formatTime(order.ordertime)}</div>
                    <div class="order-detail">${order.tablenumber}</div>
                    <div class="order-detail">${order.order_details.map((detail) => detail.menu_name).join(', ')}</div>
                    <div class="order-detail">${order.order_details.map((detail) => detail.quantity).join(', ')}</div>
                    <div class="order-detail">${order.pg}</div>
                    <div class="order-detail">${order.order_details.map((detail) => formatPrice(parseFloat(detail.menu_price) * parseInt(detail.quantity))).join(', ')}</div>
                </div>
            </div>
        `;
        orderList.insertAdjacentHTML('afterbegin', newOrderHtml);
        document.getElementById('order-count').textContent = `���� �ֹ� �Ǽ� : ${parseInt(document.getElementById('order-count').textContent.split(' ')[3]) + 1}��`;
    }

    function removeOrder(orderid) {
        const orderList = document.getElementById('order-list');
        const orderItem = document.querySelector(`.order-item[key="${orderid}"]`);
        if (orderItem) {
            orderList.removeChild(orderItem);
        }
        document.getElementById('order-count').textContent = `���� �ֹ� �Ǽ� : ${parseInt(document.getElementById('order-count').textContent.split(' ')[3]) - 1}��`;
    }
});
