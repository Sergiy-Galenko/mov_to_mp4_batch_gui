import React, { useMemo, useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";

const tabKeys = ["basic", "edit", "presets", "enhance", "metadata"] as const;

const themes = [
  { id: "netflix", name: "Netflix Dark", accent: "#e50914" },
  { id: "ember", name: "Ember", accent: "#ff6b4a" },
  { id: "ocean", name: "Ocean", accent: "#4cc9f0" },
  { id: "forest", name: "Forest", accent: "#2dd4bf" }
] as const;

type ThemeId = (typeof themes)[number]["id"];

type TabKey = (typeof tabKeys)[number];

type QueueItem = {
  id: string;
  name: string;
  path: string;
  kind: "video" | "photo";
};

type Lang = "uk" | "ru" | "en" | "pt";

const i18n = {
  uk: {
    appTitle: "Media Converter — Фото + Відео (FFmpeg)",
    appDesc: "Пакетна конвертація відео та фото через FFmpeg.",
    settingsTitle: "Налаштування інтерфейсу",
    settingsDesc: "Персоналізуй тему, шрифти, щільність і вигляд елементів.",
    settingsBtn: "Налаштування",
    filtersTitle: "Фільтри",
    enabled: "Увімкнено",
    disabled: "Вимкнено",
    filterTrim: "Trim",
    filterCrop: "Crop",
    filterResize: "Resize",
    filterSpeed: "Speed",
    filterWatermark: "Watermark",
    filterTrimDesc: "Обрізання початку/кінця",
    filterCropDesc: "Кадрування області",
    filterResizeDesc: "Зміна розміру/формату",
    filterSpeedDesc: "Прискорення або сповільнення",
    filterWatermarkDesc: "Накладення водяного знаку",
    tabs: {
      basic: "Основні",
      edit: "Редагування",
      presets: "Пресети",
      enhance: "Покращення",
      metadata: "Метадані"
    },
    ffmpeg: "FFmpeg",
    choose: "Вказати",
    check: "Перевірити",
    queue: "Черга",
    output: "Вивід",
    actions: "Дії",
    log: "Лог",
    addFiles: "Додати файли",
    addFolder: "Додати папку",
    clear: "Очистити",
    pick: "Вибрати",
    openFolder: "Відкрити папку",
    start: "Старт",
    stop: "Стоп",
    language: "Мова",
    saveChanges: "Зберегти зміни",
    saved: "Збережено"
  },
  ru: {
    appTitle: "Media Converter — Фото + Видео (FFmpeg)",
    appDesc: "Пакетная конвертация видео и фото через FFmpeg.",
    settingsTitle: "Настройки интерфейса",
    settingsDesc: "Персонализируй тему, шрифты, плотность и вид элементов.",
    settingsBtn: "Настройки",
    filtersTitle: "Фильтры",
    enabled: "Включено",
    disabled: "Выключено",
    filterTrim: "Trim",
    filterCrop: "Crop",
    filterResize: "Resize",
    filterSpeed: "Speed",
    filterWatermark: "Watermark",
    filterTrimDesc: "Обрезка начала/конца",
    filterCropDesc: "Кадрирование области",
    filterResizeDesc: "Изменение размера/формата",
    filterSpeedDesc: "Ускорение или замедление",
    filterWatermarkDesc: "Наложение водяного знака",
    tabs: {
      basic: "Основные",
      edit: "Редактирование",
      presets: "Пресеты",
      enhance: "Улучшения",
      metadata: "Метаданные"
    },
    ffmpeg: "FFmpeg",
    choose: "Указать",
    check: "Проверить",
    queue: "Очередь",
    output: "Вывод",
    actions: "Действия",
    log: "Лог",
    addFiles: "Добавить файлы",
    addFolder: "Добавить папку",
    clear: "Очистить",
    pick: "Выбрать",
    openFolder: "Открыть папку",
    start: "Старт",
    stop: "Стоп",
    language: "Язык",
    saveChanges: "Сохранить изменения",
    saved: "Сохранено"
  },
  en: {
    appTitle: "Media Converter — Photo + Video (FFmpeg)",
    appDesc: "Batch conversion of video and photos via FFmpeg.",
    settingsTitle: "Interface settings",
    settingsDesc: "Customize theme, fonts, density and appearance.",
    settingsBtn: "Settings",
    filtersTitle: "Filters",
    enabled: "Enabled",
    disabled: "Disabled",
    filterTrim: "Trim",
    filterCrop: "Crop",
    filterResize: "Resize",
    filterSpeed: "Speed",
    filterWatermark: "Watermark",
    filterTrimDesc: "Trim start/end",
    filterCropDesc: "Crop area",
    filterResizeDesc: "Resize or reformat",
    filterSpeedDesc: "Speed up or slow down",
    filterWatermarkDesc: "Apply watermark",
    tabs: {
      basic: "Basics",
      edit: "Edit",
      presets: "Presets",
      enhance: "Enhance",
      metadata: "Metadata"
    },
    ffmpeg: "FFmpeg",
    choose: "Browse",
    check: "Check",
    queue: "Queue",
    output: "Output",
    actions: "Actions",
    log: "Log",
    addFiles: "Add files",
    addFolder: "Add folder",
    clear: "Clear",
    pick: "Choose",
    openFolder: "Open folder",
    start: "Start",
    stop: "Stop",
    language: "Language",
    saveChanges: "Save changes",
    saved: "Saved"
  },
  pt: {
    appTitle: "Media Converter — Foto + Vídeo (FFmpeg)",
    appDesc: "Conversão em lote de vídeos e fotos via FFmpeg.",
    settingsTitle: "Configurações da interface",
    settingsDesc: "Personalize tema, fontes, densidade e aparência.",
    settingsBtn: "Configurações",
    filtersTitle: "Filtros",
    enabled: "Ativado",
    disabled: "Desativado",
    filterTrim: "Trim",
    filterCrop: "Crop",
    filterResize: "Resize",
    filterSpeed: "Speed",
    filterWatermark: "Watermark",
    filterTrimDesc: "Corte início/fim",
    filterCropDesc: "Corte de área",
    filterResizeDesc: "Redimensionar ou reformatar",
    filterSpeedDesc: "Acelerar ou desacelerar",
    filterWatermarkDesc: "Aplicar marca d'água",
    tabs: {
      basic: "Básico",
      edit: "Edição",
      presets: "Predefinições",
      enhance: "Melhorias",
      metadata: "Metadados"
    },
    ffmpeg: "FFmpeg",
    choose: "Selecionar",
    check: "Verificar",
    queue: "Fila",
    output: "Saída",
    actions: "Ações",
    log: "Log",
    addFiles: "Adicionar arquivos",
    addFolder: "Adicionar pasta",
    clear: "Limpar",
    pick: "Escolher",
    openFolder: "Abrir pasta",
    start: "Iniciar",
    stop: "Parar",
    language: "Idioma",
    saveChanges: "Salvar alterações",
    saved: "Salvo"
  }
} as const;

export default function App() {
  const isSettingsWindow =
    typeof window !== "undefined" &&
    new URLSearchParams(window.location.search).get("settings") === "1";

  const [activeTab, setActiveTab] = useState<TabKey>("basic");
  const [ffmpegPath, setFfmpegPath] = useState("/opt/homebrew/bin/ffmpeg");
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [outputDir, setOutputDir] = useState("~/Videos/converted");
  const [status, setStatus] = useState("Готово");
  const [fileProgress, setFileProgress] = useState(0);
  const [totalProgress, setTotalProgress] = useState(0);
  const [logLines, setLogLines] = useState<string[]>([]);
  const [uiScale, setUiScale] = useState<"compact" | "comfortable">("comfortable");
  const [buttonSize, setButtonSize] = useState<"sm" | "md" | "lg">("md");
  const [themeId, setThemeId] = useState<ThemeId>("netflix");
  const [customAccent, setCustomAccent] = useState("#e50914");
  const [selectedUpscale, setSelectedUpscale] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    trim: false,
    crop: false,
    resize: false,
    speed: false,
    watermark: false
  });
  const [fontScale, setFontScale] = useState(1);
  const [radius, setRadius] = useState(16);
  const [cardShadow, setCardShadow] = useState(0.35);
  const [maxWidth, setMaxWidth] = useState(1200);
  const [fontFamily, setFontFamily] = useState("inter");
  const [bgTone, setBgTone] = useState("dark");
  const [pattern, setPattern] = useState<"off" | "grain" | "lines">("off");
  const [glass, setGlass] = useState(false);
  const [showQueue, setShowQueue] = useState(true);
  const [showOutput, setShowOutput] = useState(true);
  const [showActions, setShowActions] = useState(true);
  const [showLog, setShowLog] = useState(true);
  const [tabStyle, setTabStyle] = useState<"pill" | "underline">("pill");
  const [lang, setLang] = useState<Lang>("uk");
  const [isDragging, setIsDragging] = useState(false);
  const [saveNotice, setSaveNotice] = useState("");

  const activeTheme = themes.find((t) => t.id === themeId) ?? themes[0];
  const accent = customAccent || activeTheme.accent;

  const totalText = useMemo(() => `${Math.round(totalProgress * 100)}%`, [totalProgress]);
  const fileText = useMemo(() => `${Math.round(fileProgress * 100)}%`, [fileProgress]);

  const applyPrefs = (prefs: any) => {
    if (prefs.uiScale) setUiScale(prefs.uiScale);
    if (prefs.buttonSize) setButtonSize(prefs.buttonSize);
    if (prefs.themeId) setThemeId(prefs.themeId);
    if (prefs.customAccent) setCustomAccent(prefs.customAccent);
    if (prefs.fontScale) setFontScale(prefs.fontScale);
    if (prefs.radius) setRadius(prefs.radius);
    if (prefs.cardShadow !== undefined) setCardShadow(prefs.cardShadow);
    if (prefs.maxWidth) setMaxWidth(prefs.maxWidth);
    if (prefs.fontFamily) setFontFamily(prefs.fontFamily);
    if (prefs.bgTone) setBgTone(prefs.bgTone);
    if (prefs.pattern) setPattern(prefs.pattern);
    if (prefs.glass !== undefined) setGlass(prefs.glass);
    if (prefs.showQueue !== undefined) setShowQueue(prefs.showQueue);
    if (prefs.showOutput !== undefined) setShowOutput(prefs.showOutput);
    if (prefs.showActions !== undefined) setShowActions(prefs.showActions);
    if (prefs.showLog !== undefined) setShowLog(prefs.showLog);
    if (prefs.tabStyle) setTabStyle(prefs.tabStyle);
    if (prefs.lang) setLang(prefs.lang);
  };

  useEffect(() => {
    const saved = localStorage.getItem("mc_prefs");
    if (!saved) return;
    try {
      applyPrefs(JSON.parse(saved));
    } catch {
      // ignore malformed prefs
    }
  }, []);

  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key !== "mc_prefs" || !event.newValue) return;
      try {
        applyPrefs(JSON.parse(event.newValue));
      } catch {
        // ignore malformed prefs
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  useEffect(() => {
    const prefs = {
      uiScale,
      buttonSize,
      themeId,
      customAccent,
      fontScale,
      radius,
      cardShadow,
      maxWidth,
      fontFamily,
      bgTone,
      pattern,
      glass,
      showQueue,
      showOutput,
      showActions,
      showLog,
      tabStyle,
      lang
    };
    localStorage.setItem("mc_prefs", JSON.stringify(prefs));
  }, [
    uiScale,
    buttonSize,
    themeId,
    customAccent,
    fontScale,
    radius,
    cardShadow,
    maxWidth,
    fontFamily,
    bgTone,
    pattern,
    glass,
    showQueue,
    showOutput,
    showActions,
    showLog,
    tabStyle,
    lang
  ]);

  useEffect(() => {
    if (isSettingsWindow) return;
    let unlistenDrop: (() => void) | null = null;
    let unlistenHover: (() => void) | null = null;
    let unlistenCancel: (() => void) | null = null;
    let unlistenLog: (() => void) | null = null;
    let unlistenProgress: (() => void) | null = null;

    const setup = async () => {
      unlistenDrop = await listen<string[]>("tauri://file-drop", (event) => {
        const paths = event.payload ?? [];
        if (paths.length === 0) return;
        const items: QueueItem[] = paths.map((path) => {
          const name = path.split("/").pop() ?? "file";
          const lower = name.toLowerCase();
          const kind: QueueItem["kind"] =
            lower.endsWith(".jpg") ||
            lower.endsWith(".jpeg") ||
            lower.endsWith(".png") ||
            lower.endsWith(".webp") ||
            lower.endsWith(".bmp")
              ? "photo"
              : "video";
          return {
            id: crypto.randomUUID(),
            name,
            path,
            kind
          };
        });
        setQueue((prev) => [...prev, ...items]);
        setStatus(`Додано файлів: ${items.length}`);
        setIsDragging(false);
      });

      unlistenHover = await listen("tauri://file-drop-hover", () => {
        setIsDragging(true);
      });

      unlistenCancel = await listen("tauri://file-drop-cancelled", () => {
        setIsDragging(false);
      });

      unlistenLog = await listen<string>("log", (event) => {
        setLogLines((prev) => [...prev.slice(-200), event.payload ?? \"\"]);
      });

      unlistenProgress = await listen<{
        file_progress: number;
        total_progress: number;
        file_text: string;
        total_text: string;
      }>(\"progress\", (event) => {
        if (!event.payload) return;
        setFileProgress(event.payload.file_progress);
        setTotalProgress(event.payload.total_progress);
      });
    };

    setup();

    return () => {
      if (unlistenDrop) unlistenDrop();
      if (unlistenHover) unlistenHover();
      if (unlistenCancel) unlistenCancel();
      if (unlistenLog) unlistenLog();
      if (unlistenProgress) unlistenProgress();
    };
  }, [isSettingsWindow]);

  const handleSaveChanges = () => {
    setSaveNotice(i18n[lang].saved);
    window.setTimeout(() => setSaveNotice(""), 1500);
  };

  const toggleFilter = (key: keyof typeof filters) => {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const safeInvoke = async <T,>(cmd: string, args?: Record<string, unknown>, fallback?: T) => {
    try {
      return await invoke<T>(cmd, args);
    } catch (error) {
      console.error(error);
      setStatus("Помилка виклику: " + cmd);
      return fallback as T;
    }
  };

  const onAddFiles = async () => {
    const items = await safeInvoke<QueueItem[]>("pick_files", undefined, [
      { id: crypto.randomUUID(), name: "sample.mp4", path: "/path/sample.mp4", kind: "video" }
    ]);
    if (items && items.length) {
      setQueue((prev) => [...prev, ...items]);
      setStatus(`Додано файлів: ${items.length}`);
    }
  };

  const onAddFolder = async () => {
    const items = await safeInvoke<QueueItem[]>("pick_folder", undefined, [
      { id: crypto.randomUUID(), name: "folder_item.jpg", path: "/path/folder_item.jpg", kind: "photo" }
    ]);
    if (items && items.length) {
      setQueue((prev) => [...prev, ...items]);
      setStatus(`Додано з папки: ${items.length}`);
    }
  };

  const onStart = async () => {
    setStatus("Запуск...");
    setFileProgress(0.0);
    setTotalProgress(0.0);
    setLogLines([]);
    await safeInvoke("start_conversion", { ffmpegPath, outputDir });
    setStatus("В роботі");
  };

  const onStop = async () => {
    await safeInvoke("stop_conversion");
    setStatus("Зупинено");
    setFileProgress(0);
    setTotalProgress(0);
  };

  return (
    <div
      className="app"
      data-density={uiScale}
      data-btn={buttonSize}
      data-theme={themeId}
      data-font={fontFamily}
      data-bg={bgTone}
      data-pattern={pattern}
      data-glass={glass ? "on" : "off"}
      data-tab-style={tabStyle}
      style={{
        ["--accent" as any]: accent,
        ["--font-scale" as any]: fontScale,
        ["--radius" as any]: `${radius}px`,
        ["--card-shadow" as any]: cardShadow,
        ["--max-width" as any]: `${maxWidth}px`
      }}
    >
      {!isSettingsWindow && (
        <div className={`drop-overlay ${isDragging ? "active" : ""}`}>
          <div className="drop-card">Перетягни файли сюди</div>
        </div>
      )}
      <header className="card header">
        <div className="header__top">
          <div>
            <h1>{isSettingsWindow ? i18n[lang].settingsTitle : i18n[lang].appTitle}</h1>
            <p>{isSettingsWindow ? i18n[lang].settingsDesc : i18n[lang].appDesc}</p>
          </div>
          {!isSettingsWindow && (
            <button className="btn secondary" onClick={() => safeInvoke("open_settings_window")}>
              {i18n[lang].settingsBtn}
            </button>
          )}
        </div>
        {!isSettingsWindow && (
          <>
            <div className="ffmpeg-row">
              <label>{i18n[lang].ffmpeg}:</label>
              <input value={ffmpegPath} onChange={(e) => setFfmpegPath(e.target.value)} />
              <button
                className="btn secondary"
                onClick={async () => {
                  const picked = await safeInvoke<string>("pick_ffmpeg", undefined, "");
                  if (picked) {
                    setFfmpegPath(picked);
                    setStatus("FFmpeg шлях оновлено");
                  }
                }}
              >
                {i18n[lang].choose}
              </button>
              <button className="btn ghost" onClick={() => safeInvoke("check_ffmpeg")}>
                {i18n[lang].check}
              </button>
            </div>
            <div className="tabs">
              {tabKeys.map((tabKey) => (
                <button
                  key={tabKey}
                  className={`tab ${activeTab === tabKey ? "active" : ""}`}
                  onClick={() => setActiveTab(tabKey)}
                >
                  {i18n[lang].tabs[tabKey]}
                </button>
              ))}
            </div>
          </>
        )}
        {isSettingsWindow && (
          <div className="customize">
            <div className="field">
              <label>{i18n[lang].language}</label>
              <div className="row">
                <button className={`btn secondary ${lang === "uk" ? "is-active" : ""}`} onClick={() => setLang("uk")}>Укр</button>
                <button className={`btn secondary ${lang === "ru" ? "is-active" : ""}`} onClick={() => setLang("ru")}>Рус</button>
                <button className={`btn secondary ${lang === "en" ? "is-active" : ""}`} onClick={() => setLang("en")}>Eng</button>
                <button className={`btn secondary ${lang === "pt" ? "is-active" : ""}`} onClick={() => setLang("pt")}>Pt</button>
              </div>
            </div>
            <div className="field">
              <label>Щільність інтерфейсу</label>
              <div className="row">
                <button className={`btn secondary ${uiScale === "compact" ? "is-active" : ""}`} onClick={() => setUiScale("compact")}>Компактний</button>
                <button className={`btn secondary ${uiScale === "comfortable" ? "is-active" : ""}`} onClick={() => setUiScale("comfortable")}>Комфортний</button>
              </div>
            </div>
            <div className="field">
              <label>Розмір кнопок</label>
              <div className="row">
                <button className={`btn secondary ${buttonSize === "sm" ? "is-active" : ""}`} onClick={() => setButtonSize("sm")}>S</button>
                <button className={`btn secondary ${buttonSize === "md" ? "is-active" : ""}`} onClick={() => setButtonSize("md")}>M</button>
                <button className={`btn secondary ${buttonSize === "lg" ? "is-active" : ""}`} onClick={() => setButtonSize("lg")}>L</button>
              </div>
            </div>
            <div className="field">
              <label>Тема</label>
              <div className="row wrap">
                {themes.map((theme) => (
                  <button
                    key={theme.id}
                    className={`btn secondary ${themeId === theme.id ? "is-active" : ""}`}
                    onClick={() => {
                      setThemeId(theme.id);
                      setCustomAccent(theme.accent);
                    }}
                  >
                    {theme.name}
                  </button>
                ))}
              </div>
            </div>
            <div className="field">
              <label>Accent колір</label>
              <div className="row">
                <input className="color-input" type="color" value={customAccent} onChange={(e) => setCustomAccent(e.target.value)} />
                <input value={customAccent} onChange={(e) => setCustomAccent(e.target.value)} placeholder="#e50914" />
              </div>
            </div>
            <div className="field">
              <label>Шрифт</label>
              <div className="row">
                <button className={`btn secondary ${fontFamily === "inter" ? "is-active" : ""}`} onClick={() => setFontFamily("inter")}>Inter</button>
                <button className={`btn secondary ${fontFamily === "plex" ? "is-active" : ""}`} onClick={() => setFontFamily("plex")}>Plex</button>
                <button className={`btn secondary ${fontFamily === "mono" ? "is-active" : ""}`} onClick={() => setFontFamily("mono")}>Mono</button>
              </div>
            </div>
            <div className="field">
              <label>Фон</label>
              <div className="row">
                <button className={`btn secondary ${bgTone === "dark" ? "is-active" : ""}`} onClick={() => setBgTone("dark")}>Dark</button>
                <button className={`btn secondary ${bgTone === "dim" ? "is-active" : ""}`} onClick={() => setBgTone("dim")}>Dim</button>
                <button className={`btn secondary ${bgTone === "light" ? "is-active" : ""}`} onClick={() => setBgTone("light")}>Light</button>
              </div>
            </div>
            <div className="field">
              <label>Патерн</label>
              <div className="row">
                <button className={`btn secondary ${pattern === "off" ? "is-active" : ""}`} onClick={() => setPattern("off")}>Off</button>
                <button className={`btn secondary ${pattern === "grain" ? "is-active" : ""}`} onClick={() => setPattern("grain")}>Grain</button>
                <button className={`btn secondary ${pattern === "lines" ? "is-active" : ""}`} onClick={() => setPattern("lines")}>Lines</button>
              </div>
            </div>
            <div className="field">
              <label>Скло (blur)</label>
              <div className="row">
                <button className={`btn secondary ${glass ? "is-active" : ""}`} onClick={() => setGlass((v) => !v)}>
                  {glass ? "Увімкнено" : "Вимкнено"}
                </button>
              </div>
            </div>
            <div className="field">
              <label>Стиль табів</label>
              <div className="row">
                <button className={`btn secondary ${tabStyle === "pill" ? "is-active" : ""}`} onClick={() => setTabStyle("pill")}>Pill</button>
                <button className={`btn secondary ${tabStyle === "underline" ? "is-active" : ""}`} onClick={() => setTabStyle("underline")}>Underline</button>
              </div>
            </div>
            <div className="field">
              <label>Показати секції</label>
              <div className="row wrap">
                <button className={`btn secondary ${showQueue ? "is-active" : ""}`} onClick={() => setShowQueue((v) => !v)}>Черга</button>
                <button className={`btn secondary ${showOutput ? "is-active" : ""}`} onClick={() => setShowOutput((v) => !v)}>Вивід</button>
                <button className={`btn secondary ${showActions ? "is-active" : ""}`} onClick={() => setShowActions((v) => !v)}>Дії</button>
                <button className={`btn secondary ${showLog ? "is-active" : ""}`} onClick={() => setShowLog((v) => !v)}>Лог</button>
              </div>
            </div>
            <div className="field">
              <label>Масштаб тексту</label>
              <input type="range" min="0.9" max="1.2" step="0.05" value={fontScale} onChange={(e) => setFontScale(Number(e.target.value))} />
            </div>
            <div className="field">
              <label>Радіус кутів</label>
              <input type="range" min="10" max="22" step="1" value={radius} onChange={(e) => setRadius(Number(e.target.value))} />
            </div>
            <div className="field">
              <label>Глибина тіні</label>
              <input type="range" min="0" max="0.6" step="0.05" value={cardShadow} onChange={(e) => setCardShadow(Number(e.target.value))} />
            </div>
            <div className="field">
              <label>Ширина макету</label>
              <input type="range" min="980" max="1400" step="20" value={maxWidth} onChange={(e) => setMaxWidth(Number(e.target.value))} />
            </div>
            <div className="field">
              <button className="btn primary" onClick={handleSaveChanges}>
                {i18n[lang].saveChanges}
              </button>
              {saveNotice && <p className="muted">{saveNotice}</p>}
            </div>
          </div>
        )}
      </header>

      {!isSettingsWindow && (
        <main className="layout">
          <section className="left">
            {showQueue && (
              <div className="card">
                <h2>{i18n[lang].queue}</h2>
                <div className="queue">
                  {queue.length === 0 ? <p className="muted">Файли не додані</p> : null}
                  {queue.map((item) => (
                    <div key={item.id} className="queue-item">
                      <span className="badge">{item.kind === "video" ? "Відео" : "Фото"}</span>
                      <span className="queue-name">{item.name}</span>
                    </div>
                  ))}
                </div>
                <div className="grid-actions">
                  <button className="btn secondary" onClick={onAddFiles}>{i18n[lang].addFiles}</button>
                  <button className="btn secondary" onClick={onAddFolder}>{i18n[lang].addFolder}</button>
                  <button className="btn ghost" onClick={() => setQueue([])}>{i18n[lang].clear}</button>
                </div>
              </div>
            )}

            {showOutput && (
              <div className="card">
                <h2>{i18n[lang].output}</h2>
                <input value={outputDir} onChange={(e) => setOutputDir(e.target.value)} />
                <div className="row">
                  <button
                    className="btn secondary"
                    onClick={async () => {
                      const picked = await safeInvoke<string>("pick_output", undefined, "");
                      if (picked) {
                        setOutputDir(picked);
                        setStatus("Вибрано папку");
                      }
                    }}
                  >
                    {i18n[lang].pick}
                  </button>
                  <button
                    className="btn ghost"
                    onClick={async () => {
                      await safeInvoke("open_output", { path: outputDir });
                    }}
                  >
                    {i18n[lang].openFolder}
                  </button>
                </div>
              </div>
            )}

            {showActions && (
              <div className="card">
                <h2>{i18n[lang].actions}</h2>
                <button className="btn primary" onClick={onStart}>{i18n[lang].start}</button>
                <button className="btn secondary" onClick={onStop}>{i18n[lang].stop}</button>
              </div>
            )}
          </section>

          <section className="right">
            <div className="card">
              <h2>Налаштування</h2>
              {activeTab === "basic" && (
                <div className="form">
                  <div className="field">
                    <label>Формат відео</label>
                    <select>
                      <option>mp4</option>
                      <option>mkv</option>
                      <option>webm</option>
                    </select>
                  </div>
                  <div className="field">
                    <label>CRF</label>
                    <input type="number" defaultValue={23} />
                  </div>
                  <div className="field">
                    <label>Preset</label>
                    <select>
                      <option>ultrafast</option>
                      <option>fast</option>
                      <option>medium</option>
                    </select>
                  </div>
                  <div className="field">
                    <label>Кодек</label>
                    <select>
                      <option>Авто</option>
                      <option>H.264</option>
                      <option>H.265</option>
                    </select>
                  </div>
                </div>
              )}

              {activeTab === "edit" && (
                <div className="form">
                  <div className="filter-grid">
                    {([
                      {
                        key: "trim",
                        title: i18n[lang].filterTrim,
                        desc: i18n[lang].filterTrimDesc
                      },
                      {
                        key: "crop",
                        title: i18n[lang].filterCrop,
                        desc: i18n[lang].filterCropDesc
                      },
                      {
                        key: "resize",
                        title: i18n[lang].filterResize,
                        desc: i18n[lang].filterResizeDesc
                      },
                      {
                        key: "speed",
                        title: i18n[lang].filterSpeed,
                        desc: i18n[lang].filterSpeedDesc
                      },
                      {
                        key: "watermark",
                        title: i18n[lang].filterWatermark,
                        desc: i18n[lang].filterWatermarkDesc
                      }
                    ] as const).map((filter) => {
                      const active = filters[filter.key];
                      return (
                        <button
                          key={filter.key}
                          className={`filter-card ${active ? "active" : ""}`}
                          onClick={() => toggleFilter(filter.key)}
                        >
                          <div>
                            <div className="filter-card__title">{filter.title}</div>
                            <div className="filter-card__desc">{filter.desc}</div>
                          </div>
                          <span className="filter-card__state">
                            {active ? i18n[lang].enabled : i18n[lang].disabled}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {activeTab === "presets" && (
                <div className="form">
                  <div className="field">
                    <label>Збережені</label>
                    <select>
                      <option>За замовчуванням</option>
                    </select>
                  </div>
                  <div className="row">
                    <button className="btn secondary">Завантажити</button>
                    <button className="btn ghost">Видалити</button>
                  </div>
                  <div className="field">
                    <label>Назва нового</label>
                    <input placeholder="Мій пресет" />
                  </div>
                  <button className="btn primary">Зберегти</button>
                </div>
              )}

              {activeTab === "enhance" && (
                <div className="form">
                  <div className="row wrap">
                    {["360p", "480p", "540p", "720p", "1080p", "4K"].map((label) => (
                      <button
                        key={label}
                        className={`btn secondary ${selectedUpscale === label ? "is-active" : ""}`}
                        onClick={() => setSelectedUpscale(label)}
                      >
                        До {label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === "metadata" && (
                <div className="form">
                  <div className="field">
                    <label>Title</label>
                    <input />
                  </div>
                  <div className="field">
                    <label>Author</label>
                    <input />
                  </div>
                  <div className="field">
                    <label>Comment</label>
                    <input />
                  </div>
                </div>
              )}
            </div>

          {showLog && (
            <div className="card">
              <h2>{i18n[lang].log}</h2>
              <textarea
                rows={8}
                readOnly
                value={logLines.length ? logLines.join("\n") : "[12:00] OK: Готово"}
              />
            </div>
          )}
          </section>
        </main>
      )}

      {!isSettingsWindow && (
        <footer className="card footer">
          <div className="status">
            <span>{status}</span>
            <div className="progress">
              <div className="progress__bar" style={{ width: `${fileProgress * 100}%` }} />
            </div>
            <span>{fileText}</span>
            <div className="progress">
              <div className="progress__bar" style={{ width: `${totalProgress * 100}%` }} />
            </div>
            <span>{totalText}</span>
          </div>
        </footer>
      )}
    </div>
  );
}
