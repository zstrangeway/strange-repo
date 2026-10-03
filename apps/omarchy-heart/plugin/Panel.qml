import QtQuick
import qs.Commons
import qs.Ui

// Heart icon in the bar that drops down a themed panel of birthdays and
// anniversaries with countdowns, using the same popup surface as the network
// and power panels. Names, dates and the title live in this widget's
// shell.json entry, never in this file.
Panel {
  id: root
  moduleName: "zstrangeway.heart"
  ipcTarget: "zstrangeway.heart"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  readonly property color fg: root.bar ? root.bar.foreground : Color.foreground
  readonly property string fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
  readonly property var monthNames: ["January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December"]

  // Midnight today; the timer below rolls it over at the date change
  property date today: midnight(new Date())

  function midnight(d) { return new Date(d.getFullYear(), d.getMonth(), d.getDate()) }

  // Accepts "YYYY-MM-DD" or "MM-DD"; year is 0 when it was left out
  function parseDate(value) {
    var parts = String(value || "").trim().split("-").map(Number)
    if (parts.length === 3 && parts.every(isFinite)) return { year: parts[0], month: parts[1] - 1, day: parts[2] }
    if (parts.length === 2 && parts.every(isFinite)) return { year: 0, month: parts[0] - 1, day: parts[1] }
    return null
  }

  function nextOccurrence(d) {
    var next = new Date(today.getFullYear(), d.month, d.day)
    if (next < today) next = new Date(today.getFullYear() + 1, d.month, d.day)
    return next
  }

  function daysUntil(d) { return Math.round((nextOccurrence(d) - today) / 86400000) }

  function countdownText(d) {
    var days = daysUntil(d)
    return days === 0 ? "\uD83C\uDF89 Today" : days === 1 ? "Tomorrow" : days + " days"
  }

  // Completed years as of today: current age, or years together
  function yearsSince(d) {
    var years = today.getFullYear() - d.year
    if (today < new Date(today.getFullYear(), d.month, d.day)) years -= 1
    return years
  }

  // "April 12, 1990 (36)"; just "April 12" when the year is unknown
  function detailText(d) {
    var text = monthNames[d.month] + " " + d.day
    if (d.year > 0) text += ", " + d.year + " (" + yearsSince(d) + ")"
    return text
  }

  // people: [{ "name": "Alex", "birthday": "1990-04-12", "anniversary": "2015-06-20" }, ...]
  readonly property var people: {
    var list = []
    var entries = setting("people", [])
    for (var i = 0; i < entries.length; i++) {
      var details = []
      var birthday = parseDate(entries[i].birthday)
      var anniversary = parseDate(entries[i].anniversary)
      if (birthday) details.push({ icon: "\uf1fd", date: birthday })
      if (anniversary) details.push({ icon: "\uf004", date: anniversary })
      if (details.length > 0) list.push({ name: entries[i].name, details: details })
    }
    return list
  }

  // Days to the nearest date across everyone; drives the bar icon's state
  readonly property int soonestDays: {
    var soonest = -1
    for (var i = 0; i < people.length; i++)
      for (var j = 0; j < people[i].details.length; j++) {
        var days = daysUntil(people[i].details[j].date)
        if (soonest < 0 || days < soonest) soonest = days
      }
    return soonest
  }
  readonly property bool comingUp: soonestDays >= 0 && soonestDays <= setting("soonDays", 7)
  readonly property bool celebrating: soonestDays === 0

  function refreshToday() {
    var now = midnight(new Date())
    if (now.getTime() !== today.getTime()) today = now
  }

  onOpenedChanged: if (opened) refreshToday()

  Timer {
    interval: 60000
    running: true
    repeat: true
    onTriggered: root.refreshToday()
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\uf004"
    tooltipText: ""
    // Accent-colored heart when a date is within soonDays
    active: root.comingUp
    activeColor: Color.accent
    onPressed: function(b) { root.toggle() }

    // Gentle pulse on the day itself
    SequentialAnimation on opacity {
      running: root.celebrating
      loops: Animation.Infinite
      alwaysRunToEnd: true
      NumberAnimation { to: 0.35; duration: 900; easing.type: Easing.InOutSine }
      NumberAnimation { to: 1.0; duration: 900; easing.type: Easing.InOutSine }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(340))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(14)

        Canvas {
          id: heart
          anchors.horizontalCenter: parent.horizontalCenter
          width: Style.space(180)
          height: Style.space(160)

          readonly property color fill: Color.accent
          readonly property color edge: root.bar ? root.bar.foreground : Color.foreground
          onFillChanged: requestPaint()
          onEdgeChanged: requestPaint()

          // Parametric heart curve, scaled to fit the canvas
          onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            var s = Math.min(width / 34, height / 31)
            var cx = width / 2
            var cy = height * 0.42
            ctx.beginPath()
            for (var i = 0; i <= 360; i++) {
              var t = i * Math.PI / 180
              var x = 16 * Math.pow(Math.sin(t), 3)
              var y = 13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)
              if (i === 0) ctx.moveTo(cx + x * s, cy - y * s)
              else ctx.lineTo(cx + x * s, cy - y * s)
            }
            ctx.closePath()
            ctx.fillStyle = fill
            ctx.fill()
            ctx.lineWidth = Math.max(1, Style.space(2))
            ctx.strokeStyle = edge
            ctx.stroke()
          }
        }

        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          text: root.setting("title", "I \u2665 You")
          color: root.fg
          font.family: root.fontFamily
          font.pixelSize: Style.font.title
          font.bold: true
        }

        PanelSeparator {
          width: parent.width
          visible: root.people.length > 0
          foreground: root.fg
        }

        Repeater {
          model: root.people

          Column {
            id: person
            required property var modelData
            width: column.width
            spacing: Style.space(6)

            Text {
              text: person.modelData.name
              color: root.fg
              font.family: root.fontFamily
              font.pixelSize: Style.font.title
              font.bold: true
            }

            Repeater {
              model: person.modelData.details

              Item {
                id: detailRow
                required property var modelData
                readonly property bool isToday: root.daysUntil(modelData.date) === 0
                width: person.width
                implicitHeight: Math.max(detailLabels.implicitHeight, detailCountdown.implicitHeight)
                  + (isToday ? Style.space(8) : 0)

                // Accent wash behind the row on the day itself
                Rectangle {
                  anchors.fill: parent
                  visible: detailRow.isToday
                  radius: Style.space(4)
                  color: Qt.rgba(Color.accent.r, Color.accent.g, Color.accent.b, 0.18)
                }

                Text {
                  id: detailIcon
                  text: modelData.icon
                  color: Color.accent
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  anchors.left: parent.left
                  anchors.leftMargin: Style.space(4)
                  anchors.verticalCenter: parent.verticalCenter
                  width: Style.space(22)
                }

                Text {
                  id: detailLabels
                  anchors.left: detailIcon.right
                  anchors.right: detailCountdown.left
                  anchors.rightMargin: Style.space(10)
                  anchors.verticalCenter: parent.verticalCenter
                  text: root.detailText(modelData.date)
                  color: root.fg
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  elide: Text.ElideRight
                }

                Text {
                  id: detailCountdown
                  text: root.countdownText(modelData.date)
                  color: Color.accent
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.subtitle
                  font.bold: true
                  anchors.right: parent.right
                  anchors.rightMargin: detailRow.isToday ? Style.space(6) : 0
                  anchors.verticalCenter: parent.verticalCenter
                }
              }
            }
          }
        }
      }
    }
  }
}
