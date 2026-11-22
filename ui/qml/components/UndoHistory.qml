import QtQuick 2.15

// Value snapshots only: playback, navigation and running jobs are not edits.
QtObject {
    id: root
    property var capture: function() { return ({}) }
    property var restore: function(state) {}
    property bool initialized: false
    property bool restoring: false
    property int transactionDepth: 0
    property int limit: 100
    property string current: ""
    property var past: []
    property var future: []
    readonly property bool canUndo: past.length > 0 || (initialized && pending.running)
    readonly property bool canRedo: future.length > 0 && !pending.running
    property Timer pending: Timer {
        interval: 300
        onTriggered: root.flush()
    }
    function reset() {
        pending.stop()
        transactionDepth = 0
        current = JSON.stringify(capture())
        past = []
        future = []
        initialized = true
    }
    function schedule() {
        if (initialized && !restoring && transactionDepth === 0)
            pending.restart()
    }
    function flush() {
        pending.stop()
        if (!initialized || restoring) return
        var next = JSON.stringify(capture())
        if (next === current) return
        past = past.concat([current]).slice(-limit)
        current = next
        future = []
    }
    function begin() {
        if (transactionDepth === 0) flush()
        transactionDepth++
    }
    function end() {
        transactionDepth = Math.max(0, transactionDepth - 1)
        if (transactionDepth === 0) flush()
    }
    // System recommendations become the baseline without erasing user edits.
    function rebase(patch) {
        if (!initialized) return
        pending.stop()
        function updated(value) {
            var state = JSON.parse(value)
            for (var key in patch) state[key] = patch[key]
            return JSON.stringify(state)
        }
        function compact(values) {
            return values.map(updated).filter(function(value, index, array) {
                return index === 0 || value !== array[index - 1]
            })
        }
        current = JSON.stringify(capture())
        var previous = compact(past)
        var next = compact(future)
        while (previous.length && previous[previous.length - 1] === current) previous.pop()
        while (next.length && next[next.length - 1] === current) next.pop()
        past = previous
        future = next
    }
    function apply(snapshot) {
        restoring = true
        try {
            restore(JSON.parse(snapshot))
            current = JSON.stringify(capture())
        } finally {
            pending.stop()
            restoring = false
        }
    }
    function undo() {
        flush()
        if (!past.length) return
        future = future.concat([current])
        var previous = past[past.length - 1]
        past = past.slice(0, -1)
        apply(previous)
    }
    function redo() {
        flush()
        if (!future.length) return
        past = past.concat([current]).slice(-limit)
        var next = future[future.length - 1]
        future = future.slice(0, -1)
        apply(next)
    }
}
