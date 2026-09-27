import QtQuick 2.15
EditorField {
    id: control
    property real value: 0
    property real minimum: 0
    property real maximum: 100000
    property int decimals: 0
    signal edited(real number)
    text: Number(value).toFixed(decimals)
    inputMethodHints: Qt.ImhFormattedNumbersOnly
    validator: DoubleValidator { bottom: control.minimum; top: control.maximum; decimals: control.decimals; locale: "C" }
    onEditingFinished: {
        var number = Number(text)
        if (isFinite(number)) edited(Math.max(minimum, Math.min(maximum, number)))
        text = Number(value).toFixed(decimals)
    }
    onValueChanged: if (!activeFocus) text = Number(value).toFixed(decimals)
}
