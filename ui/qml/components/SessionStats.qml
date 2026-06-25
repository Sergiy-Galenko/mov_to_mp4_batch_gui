import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import App 1.0

Rectangle {
    id: root
    property int doneCount: 0
    property int failedCount: 0
    property int skippedCount: 0
    property int totalCount: 0
    property string elapsedText: "00:00"
    property string etaText: "--:--"
    property string avgSpeedText: "--"
    property string savedText: "0 B"
    property string inputText: "0 B"
    property string outputText: "0 B"

    implicitHeight: 92
    radius: Theme.radiusPanel
    color: Theme.bgSurface
    border.width: 1
    border.color: Theme.bgBorder

    GridLayout {
        anchors.fill: parent
        anchors.margins: 12
        columns: 3
        rowSpacing: 8
        columnSpacing: 12

        StatCell { label: I18n.t("done"); value: root.doneCount + "/" + root.totalCount; accent: Theme.accentSuccess }
        StatCell { label: I18n.t("failed"); value: root.failedCount; accent: Theme.accentError }
        StatCell { label: I18n.t("skipped"); value: root.skippedCount; accent: Theme.accentWarn }
        StatCell { label: I18n.t("elapsed"); value: root.elapsedText; accent: Theme.textSecondary }
        StatCell { label: I18n.t("eta"); value: root.etaText; accent: Theme.accentWarn }
        StatCell { label: I18n.t("avg"); value: root.avgSpeedText; accent: Theme.accentPrimary }
        StatCell { label: I18n.t("saved"); value: root.savedText; accent: Theme.accentSuccess }
        StatCell { label: I18n.t("input"); value: root.inputText; accent: Theme.textSecondary }
        StatCell { label: I18n.t("out"); value: root.outputText; accent: Theme.accentPurple }
    }
}
