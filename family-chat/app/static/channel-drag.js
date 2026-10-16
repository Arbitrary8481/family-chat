// Drag-and-drop for channel lists, shared by the admin panel's Channels
// tab and the chat's own Settings → Channels tab.
//
// Expects root to contain one .channel-category-group-list[data-category-id]
// per category, each holding .channel-drag-row[data-slug] rows with a
// .drag-handle inside. After each drop, calls onDrop with the full new
// order, {category_id: [slug, ...]}, for the caller to save.
//
// Pointer events rather than the native HTML5 Drag and Drop API, which
// has a long history of being unreliable on touchscreens; pointer events
// fire the same way for mouse and touch. Listens on root itself, so the
// rows inside can be re-rendered freely without re-initializing.
function initChannelDragDrop(root, onDrop) {
    if (!root || root.dataset.channelDragReady) return;
    root.dataset.channelDragReady = '1';

    const DRAG_THRESHOLD_PX = 6;
    let dragRow = null;
    let placeholder = null;
    let pointerId = null;
    let grabOffsetX = 0, grabOffsetY = 0;
    let startPointerX = 0, startPointerY = 0;
    let startRect = null;
    let dragging = false;

    function lists() {
        return Array.from(root.querySelectorAll('.channel-category-group-list'));
    }

    // Shows a "Drag a channel here" box in every category that's
    // currently empty, so there's always something to drop onto.
    function syncEmptyPlaceholders() {
        lists().forEach(list => {
            const hasRow = !!list.querySelector('.channel-drag-row, .channel-drag-placeholder');
            let empty = list.querySelector('.channel-category-group-empty');
            if (hasRow) {
                if (empty) empty.remove();
            } else if (!empty) {
                empty = document.createElement('div');
                empty.className = 'channel-category-group-empty';
                empty.textContent = 'Drag a channel here';
                list.appendChild(empty);
            }
        });
    }

    function onPointerDown(e) {
        const handle = e.target.closest('.drag-handle');
        const row = handle && handle.closest('.channel-drag-row');
        if (!row || !root.contains(row)) return;
        if (e.button !== undefined && e.button !== 0) return;

        dragRow = row;
        pointerId = e.pointerId;
        dragging = false;
        startPointerX = e.clientX;
        startPointerY = e.clientY;
        startRect = row.getBoundingClientRect();
        grabOffsetX = e.clientX - startRect.left;
        grabOffsetY = e.clientY - startRect.top;

        document.addEventListener('pointermove', onPointerMove);
        document.addEventListener('pointerup', onPointerUp);
        document.addEventListener('pointercancel', onPointerUp);
    }

    function activateDrag() {
        dragging = true;
        placeholder = document.createElement('div');
        placeholder.className = 'channel-drag-placeholder';
        placeholder.style.height = startRect.height + 'px';
        dragRow.parentNode.insertBefore(placeholder, dragRow);

        dragRow.classList.add('channel-row-dragging');
        dragRow.style.width = startRect.width + 'px';
        dragRow.style.left = startRect.left + 'px';
        dragRow.style.top = startRect.top + 'px';
        // Out of its list while it floats, so it doesn't count as a row
        // of the category it came from.
        document.body.appendChild(dragRow);
    }

    function onPointerMove(e) {
        if (!dragRow || e.pointerId !== pointerId) return;
        if (!dragging) {
            const dx = e.clientX - startPointerX;
            const dy = e.clientY - startPointerY;
            if (Math.abs(dx) < DRAG_THRESHOLD_PX && Math.abs(dy) < DRAG_THRESHOLD_PX) return;
            activateDrag();
        }
        e.preventDefault();
        dragRow.style.left = (e.clientX - grabOffsetX) + 'px';
        dragRow.style.top = (e.clientY - grabOffsetY) + 'px';
        positionPlaceholder(e.clientX, e.clientY);
    }

    // Picks the category list under the pointer (or the vertically
    // closest one, so a touch drag that strays slightly outside every
    // list doesn't freeze) and places the gap before the first row
    // whose midpoint is below the pointer.
    function positionPlaceholder(x, y) {
        const allLists = lists();
        let target = allLists.find(list => {
            const r = list.getBoundingClientRect();
            return x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
        });
        if (!target) {
            let bestDist = Infinity;
            allLists.forEach(list => {
                const r = list.getBoundingClientRect();
                const dist = Math.abs(y - (r.top + r.bottom) / 2);
                if (dist < bestDist) {
                    bestDist = dist;
                    target = list;
                }
            });
        }
        if (!target) return;

        allLists.forEach(list => list.classList.toggle('channel-group-drop-target', list === target));

        const before = Array.from(target.querySelectorAll('.channel-drag-row')).find(row => {
            const r = row.getBoundingClientRect();
            return y < r.top + r.height / 2;
        });
        if (before) {
            target.insertBefore(placeholder, before);
        } else {
            target.appendChild(placeholder);
        }
        syncEmptyPlaceholders();
    }

    function onPointerUp(e) {
        if (!dragRow || e.pointerId !== pointerId) return;
        document.removeEventListener('pointermove', onPointerMove);
        document.removeEventListener('pointerup', onPointerUp);
        document.removeEventListener('pointercancel', onPointerUp);
        lists().forEach(list => list.classList.remove('channel-group-drop-target'));

        const row = dragRow;
        const wasDragging = dragging;
        dragRow = null;
        dragging = false;
        pointerId = null;
        // A tap on the handle that never moved past the threshold.
        if (!wasDragging) return;

        row.classList.remove('channel-row-dragging');
        row.style.left = '';
        row.style.top = '';
        row.style.width = '';
        if (placeholder && placeholder.parentNode) {
            placeholder.parentNode.insertBefore(row, placeholder);
            placeholder.remove();
        }
        placeholder = null;
        syncEmptyPlaceholders();
        onDrop(currentOrder());
    }

    function currentOrder() {
        const result = {};
        lists().forEach(list => {
            result[list.dataset.categoryId] = Array.from(list.querySelectorAll('.channel-drag-row'))
                .map(row => row.dataset.slug);
        });
        return result;
    }

    root.addEventListener('pointerdown', onPointerDown);
}
