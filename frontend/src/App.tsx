import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  CheckCircle,
  ClipboardList,
  Download,
  Eye,
  FileText,
  Home,
  LogOut,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Send,
  ShieldCheck,
  UploadCloud,
  Users,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api, currentToken, setAuthToken } from "./api";
import type {
  AIAnalysis,
  AnalyticsOverview,
  AuditLog,
  FeedbackType,
  Pathology,
  Report,
  Role,
  Study,
  StudyStatus,
  User
} from "./types";

type View = "dashboard" | "reference" | "analytics" | "audit" | "users";

const ROLE_LABELS: Record<Role, string> = {
  admin: "Администратор",
  radiologist: "Рентгенолог",
  physician: "Врач-пользователь",
  expert: "Эксперт",
  student: "Студент",
  analyst: "Аналитик"
};

const STATUS_LABELS: Record<StudyStatus, string> = {
  created: "создан",
  uploaded: "загружен",
  checked: "проверен",
  ready_for_analysis: "готов к анализу",
  analyzing: "анализируется",
  ai_completed: "AI готов",
  draft_ready: "черновик готов",
  confirmed: "подтвержден",
  exported: "экспортирован",
  failed: "ошибка"
};

const FINDING_LABELS: Record<string, string> = {
  normal: "Норма",
  pneumonia: "Пневмония",
  pleural_effusion: "Плевральный выпот",
  pneumothorax: "Пневмоторакс",
  atelectasis: "Ателектаз"
};

const FEEDBACK_LABELS: Record<FeedbackType, string> = {
  false_positive: "Ложноположительный",
  false_negative: "Ложноотрицательный",
  wrong_region: "Неверная зона",
  other: "Другое"
};

function formatDate(value: string | null | undefined) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

function parseProbabilities(value: string | null): [string, number][] {
  if (!value) return [];
  try {
    const parsed = JSON.parse(value) as Record<string, number>;
    return Object.entries(parsed).sort((a, b) => b[1] - a[1]);
  } catch {
    return [];
  }
}

function canEditFinal(user: User | null) {
  return Boolean(user && ["radiologist", "expert"].includes(user.role));
}

function canUseClinicalFlow(user: User | null) {
  return Boolean(user && ["admin", "radiologist", "physician", "expert"].includes(user.role));
}

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [login, setLogin] = useState("radiologist");
  const [password, setPassword] = useState("radio123");
  const [view, setView] = useState<View>("dashboard");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const [studies, setStudies] = useState<Study[]>([]);
  const [selectedStudy, setSelectedStudy] = useState<Study | null>(null);
  const [aiResults, setAiResults] = useState<AIAnalysis[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [finalText, setFinalText] = useState("");
  const [pathologies, setPathologies] = useState<Pathology[]>([]);
  const [audit, setAudit] = useState<AuditLog[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [users, setUsers] = useState<User[]>([]);

  const [filters, setFilters] = useState({ status: "", study_type: "", date_from: "", date_to: "" });
  const [newStudy, setNewStudy] = useState({ patient_code: "DEMO-001", study_type: "ОГК", clinical_note: "" });
  const [newFile, setNewFile] = useState<File | null>(null);
  const [autoAI, setAutoAI] = useState(true);
  const [feedbackType, setFeedbackType] = useState<FeedbackType>("false_positive");
  const [feedbackComment, setFeedbackComment] = useState("");

  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [drag, setDrag] = useState<{ x: number; y: number } | null>(null);
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [showHeatmap, setShowHeatmap] = useState(false);

  const latestAI = aiResults[0] ?? null;
  const probabilityRows = useMemo(() => parseProbabilities(latestAI?.probabilities_json ?? null), [latestAI]);

  useEffect(() => {
    async function restore() {
      if (!currentToken()) {
        setBooting(false);
        return;
      }
      try {
        const me = await api.me();
        setUser(me);
        await loadInitial(me);
      } catch {
        setAuthToken("");
      } finally {
        setBooting(false);
      }
    }
    restore();
  }, []);

  async function loadInitial(nextUser = user) {
    await Promise.all([loadStudies(), loadPathologies()]);
    if (nextUser && ["admin", "analyst", "expert"].includes(nextUser.role)) {
      await loadAnalytics();
    }
  }

  function flash(message: string) {
    setNotice(message);
    setError("");
  }

  function fail(err: unknown) {
    setError(err instanceof Error ? err.message : "Неизвестная ошибка");
    setNotice("");
  }

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const response = await api.login(login, password);
      setAuthToken(response.access_token);
      setUser(response.user);
      await loadInitial(response.user);
      flash("Вход выполнен");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    setAuthToken("");
    setUser(null);
    setSelectedStudy(null);
    setStudies([]);
    setPreviewUrl(null);
  }

  async function loadStudies(nextFilters = filters) {
    const params = Object.fromEntries(Object.entries(nextFilters).filter(([, value]) => value));
    const data = await api.listStudies(params);
    setStudies(data);
  }

  async function loadPathologies() {
    const data = await api.listPathologies();
    setPathologies(data);
  }

  async function loadAnalytics() {
    const data = await api.analytics();
    setAnalytics(data);
  }

  async function loadAudit() {
    const data = await api.audit();
    setAudit(data);
  }

  async function loadUsers() {
    const data = await api.listUsers();
    setUsers(data);
  }

  async function openStudy(studyId: number) {
    setBusy(true);
    try {
      const detail = await api.getStudy(studyId);
      setSelectedStudy(detail);
      setView("dashboard");
      setAiResults(await api.listAI(studyId));
      await loadPreview(studyId);
      try {
        const nextReport = await api.getReport(studyId);
        setReport(nextReport);
        setFinalText(nextReport.final_text ?? "");
      } catch {
        setReport(null);
        setFinalText("");
      }
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function loadPreview(studyId: number) {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
    }
    try {
      const blob = await api.previewImage(studyId);
      setPreviewUrl(URL.createObjectURL(blob));
    } catch {
      setPreviewUrl(null);
    }
  }

  async function createAndUpload(event: FormEvent) {
    event.preventDefault();
    if (!newFile) {
      setError("Выберите DICOM, JPEG или PNG файл");
      return;
    }
    setBusy(true);
    try {
      const created = await api.createStudy(newStudy);
      const uploaded = await api.uploadImage(created.id, newFile);
      setNewFile(null);
      setSelectedStudy(uploaded);
      await loadPreview(uploaded.id);
      let analysis: AIAnalysis | null = null;
      if (autoAI) {
        analysis = await api.runAI(uploaded.id, true, true);
        setAiResults([analysis]);
        try {
          const draft = await api.createDraft(uploaded.id);
          setReport(draft);
          setFinalText(draft.final_text ?? "");
        } catch {
          setReport(null);
        }
      }
      setSelectedStudy(await api.getStudy(uploaded.id));
      await loadStudies();
      flash(analysis ? "Файл загружен, AI-анализ выполнен" : "Файл загружен и проверен");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function runAI(auto = false) {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      const analysis = await api.runAI(selectedStudy.id, true, auto);
      setAiResults([analysis, ...aiResults]);
      const detail = await api.getStudy(selectedStudy.id);
      setSelectedStudy(detail);
      await loadStudies();
      flash("AI-анализ завершен");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function createDraft() {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      const nextReport = await api.createDraft(selectedStudy.id);
      setReport(nextReport);
      setFinalText(nextReport.final_text ?? "");
      setSelectedStudy(await api.getStudy(selectedStudy.id));
      await loadStudies();
      flash("AI-черновик создан");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function saveReport() {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      const nextReport = await api.saveReport(selectedStudy.id, finalText);
      setReport(nextReport);
      setSelectedStudy(await api.getStudy(selectedStudy.id));
      await loadStudies();
      flash("Финальный текст сохранен");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function confirmReport() {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      const nextReport = await api.confirmReport(selectedStudy.id);
      setReport(nextReport);
      setSelectedStudy(await api.getStudy(selectedStudy.id));
      await loadStudies();
      flash("Заключение подтверждено врачом");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function exportReport(format: "pdf" | "docx") {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      const blob = await api.exportReport(selectedStudy.id, format);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${selectedStudy.accession_number}.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
      await loadStudies();
      flash(`Экспорт ${format.toUpperCase()} готов`);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function sendFeedback() {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      await api.sendFeedback(selectedStudy.id, {
        analysis_id: latestAI?.id,
        feedback_type: feedbackType,
        comment: feedbackComment || undefined
      });
      setFeedbackComment("");
      flash("Обратная связь сохранена");
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  function resetViewer() {
    setZoom(1);
    setPan({ x: 0, y: 0 });
    setBrightness(100);
    setContrast(100);
  }

  if (booting) {
    return <div className="boot">Загрузка системы...</div>;
  }

  if (!user) {
    return (
      <main className="loginShell">
        <form className="loginPanel" onSubmit={handleLogin}>
          <div>
            <p className="eyebrow">Radiology AI Assistant</p>
            <h1>Рабочее место анализа ОГК</h1>
          </div>
          <label>
            Логин
            <input value={login} onChange={(event) => setLogin(event.target.value)} />
          </label>
          <label>
            Пароль
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <button className="primaryButton" disabled={busy}>
            <ShieldCheck size={18} />
            Войти
          </button>
          <p className="hint">Демо: radiologist / radio123, doctor / doctor123, admin / admin123</p>
          {error && <div className="errorLine">{error}</div>}
        </form>
      </main>
    );
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brandMark">RX</div>
          <div>
            <strong>Radiology AI</strong>
            <span>{ROLE_LABELS[user.role]}</span>
          </div>
        </div>
        <nav>
          <NavButton active={view === "dashboard"} icon={<Home size={18} />} label="Исследования" onClick={() => setView("dashboard")} />
          <NavButton active={view === "reference"} icon={<BookOpen size={18} />} label="Справочник" onClick={() => setView("reference")} />
          {["admin", "analyst", "expert"].includes(user.role) && (
            <NavButton
              active={view === "analytics"}
              icon={<BarChart3 size={18} />}
              label="Аналитика"
              onClick={async () => {
                setView("analytics");
                await loadAnalytics();
              }}
            />
          )}
          {["admin", "analyst"].includes(user.role) && (
            <NavButton
              active={view === "audit"}
              icon={<ClipboardList size={18} />}
              label="Аудит"
              onClick={async () => {
                setView("audit");
                await loadAudit();
              }}
            />
          )}
          {user.role === "admin" && (
            <NavButton
              active={view === "users"}
              icon={<Users size={18} />}
              label="Пользователи"
              onClick={async () => {
                setView("users");
                await loadUsers();
              }}
            />
          )}
        </nav>
        <button className="ghostButton" onClick={logout}>
          <LogOut size={18} />
          Выйти
        </button>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{viewTitle(view)}</h1>
            <p>{user.full_name}</p>
          </div>
          <div className="topActions">
            <button className="ghostButton" onClick={() => loadInitial()}>
              <RefreshCw size={18} />
              Обновить
            </button>
          </div>
        </header>

        {notice && <div className="notice">{notice}</div>}
        {error && <div className="errorLine">{error}</div>}

        {view === "dashboard" && (
          <section className="dashboardGrid">
            <div className="leftColumn">
              {canUseClinicalFlow(user) && (
                <form className="toolPanel" onSubmit={createAndUpload}>
                  <div className="panelHeader">
                    <h2>Новый снимок</h2>
                    <UploadCloud size={20} />
                  </div>
                  <div className="formGrid">
                    <label>
                      Код пациента
                      <input value={newStudy.patient_code} onChange={(event) => setNewStudy({ ...newStudy, patient_code: event.target.value })} />
                    </label>
                    <label>
                      Тип
                      <select value={newStudy.study_type} onChange={(event) => setNewStudy({ ...newStudy, study_type: event.target.value })}>
                        <option value="ОГК">ОГК</option>
                        <option value="ОГК demo">ОГК demo</option>
                      </select>
                    </label>
                  </div>
                  <label>
                    Клиническая заметка
                    <textarea
                      value={newStudy.clinical_note}
                      onChange={(event) => setNewStudy({ ...newStudy, clinical_note: event.target.value })}
                      rows={3}
                    />
                  </label>
                  <label className="fileDrop">
                    <UploadCloud size={22} />
                    <span>{newFile ? newFile.name : "DICOM / JPEG / PNG"}</span>
                    <input
                      type="file"
                      accept=".dcm,.dicom,.jpg,.jpeg,.png,image/png,image/jpeg"
                      onChange={(event) => setNewFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <label className="checkLine">
                    <input type="checkbox" checked={autoAI} onChange={(event) => setAutoAI(event.target.checked)} />
                    Авто AI после загрузки
                  </label>
                  <button className="primaryButton" disabled={busy}>
                    <Plus size={18} />
                    Создать и загрузить
                  </button>
                </form>
              )}

              <div className="toolPanel">
                <div className="panelHeader">
                  <h2>Фильтры</h2>
                  <Search size={20} />
                </div>
                <div className="filterGrid">
                  <select
                    value={filters.status}
                    onChange={(event) => setFilters({ ...filters, status: event.target.value })}
                  >
                    <option value="">Все статусы</option>
                    {Object.entries(STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <input
                    placeholder="Тип"
                    value={filters.study_type}
                    onChange={(event) => setFilters({ ...filters, study_type: event.target.value })}
                  />
                  <input type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} />
                  <input type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} />
                </div>
                <button className="ghostButton" onClick={() => loadStudies()} disabled={busy}>
                  <Search size={18} />
                  Применить
                </button>
              </div>

              <div className="studyList">
                {studies.map((study) => (
                  <button
                    className={`studyRow ${selectedStudy?.id === study.id ? "active" : ""}`}
                    key={study.id}
                    onClick={() => openStudy(study.id)}
                  >
                    <span>
                      <strong>{study.accession_number}</strong>
                      <small>{study.patient_code} · {study.study_type}</small>
                    </span>
                    <StatusBadge status={study.status} />
                  </button>
                ))}
                {!studies.length && <div className="emptyState">Нет исследований для выбранных фильтров</div>}
              </div>
            </div>

            <div className="rightColumn">
              {selectedStudy ? (
                <>
                  <section className="viewerPanel">
                    <div className="panelHeader">
                      <div>
                        <h2>{selectedStudy.accession_number}</h2>
                        <p>{selectedStudy.patient_code} · {STATUS_LABELS[selectedStudy.status]}</p>
                      </div>
                      <StatusBadge status={selectedStudy.status} />
                    </div>
                    <div className="viewerToolbar">
                      <IconButton label="Увеличить" onClick={() => setZoom((value) => Math.min(value + 0.15, 3))}>
                        <ZoomIn size={18} />
                      </IconButton>
                      <IconButton label="Уменьшить" onClick={() => setZoom((value) => Math.max(value - 0.15, 0.4))}>
                        <ZoomOut size={18} />
                      </IconButton>
                      <IconButton label="Сбросить" onClick={resetViewer}>
                        <RotateCcw size={18} />
                      </IconButton>
                      <IconButton label="Heatmap" active={showHeatmap} onClick={() => setShowHeatmap((value) => !value)}>
                        <Eye size={18} />
                      </IconButton>
                      <label>
                        Яркость
                        <input type="range" min="50" max="160" value={brightness} onChange={(event) => setBrightness(Number(event.target.value))} />
                      </label>
                      <label>
                        Контраст
                        <input type="range" min="50" max="180" value={contrast} onChange={(event) => setContrast(Number(event.target.value))} />
                      </label>
                    </div>
                    <div
                      className="imageStage"
                      onMouseDown={(event) => setDrag({ x: event.clientX - pan.x, y: event.clientY - pan.y })}
                      onMouseMove={(event) => {
                        if (drag) setPan({ x: event.clientX - drag.x, y: event.clientY - drag.y });
                      }}
                      onMouseUp={() => setDrag(null)}
                      onMouseLeave={() => setDrag(null)}
                    >
                      {previewUrl ? (
                        <>
                          <img
                            src={previewUrl}
                            alt="Рентгенологическое изображение"
                            style={{
                              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                              filter: `brightness(${brightness}%) contrast(${contrast}%)`
                            }}
                          />
                          {showHeatmap && (
                            <div
                              className="heatmapOverlay"
                              style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
                            />
                          )}
                        </>
                      ) : (
                        <div className="emptyState">Превью пока недоступно</div>
                      )}
                    </div>
                  </section>

                  <section className="clinicalGrid">
                    <div className="toolPanel">
                      <div className="panelHeader">
                        <h2>AI-анализ</h2>
                        <Activity size={20} />
                      </div>
                      <div className="disclaimer">
                        <AlertTriangle size={18} />
                        <strong>Результат является предварительной подсказкой. Окончательное решение принимает только врач</strong>
                      </div>
                      <button className="primaryButton" onClick={() => runAI(false)} disabled={busy}>
                        <Play size={18} />
                        Запустить AI
                      </button>
                      {latestAI && (
                        <div className="aiResult">
                          <div className="metricLine">
                            <span>Статус</span>
                            <strong>{latestAI.status}</strong>
                          </div>
                          {latestAI.hidden_due_low_confidence ? (
                            <div className="warningBox">{latestAI.warning}</div>
                          ) : (
                            <div className="prediction">
                              {latestAI.predicted_class ? FINDING_LABELS[latestAI.predicted_class] : "Класс не определен"}
                            </div>
                          )}
                          <div className="metricLine">
                            <span>Уверенность</span>
                            <strong>{formatPercent(latestAI.confidence)}</strong>
                          </div>
                          <div className="metricLine">
                            <span>Порог</span>
                            <strong>{formatPercent(latestAI.threshold)}</strong>
                          </div>
                          <small>Модель: {latestAI.model_version} · Данные: {latestAI.dataset_version}</small>
                          <div className="probabilityList">
                            {probabilityRows.map(([label, score]) => (
                              <div key={label}>
                                <span>{FINDING_LABELS[label] ?? label}</span>
                                <meter min={0} max={1} value={score} />
                                <b>{formatPercent(score)}</b>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <button className="ghostButton" onClick={createDraft} disabled={busy || !latestAI}>
                        <FileText size={18} />
                        Создать черновик
                      </button>
                    </div>

                    <div className="toolPanel reportPanel">
                      <div className="panelHeader">
                        <h2>Заключение</h2>
                        <FileText size={20} />
                      </div>
                      <label>
                        AI-черновик
                        <textarea value={report?.ai_draft_text ?? ""} readOnly rows={8} />
                      </label>
                      <label>
                        Финальный текст врача
                        <textarea
                          value={finalText}
                          onChange={(event) => setFinalText(event.target.value)}
                          readOnly={!canEditFinal(user)}
                          rows={9}
                        />
                      </label>
                      <div className="buttonRow">
                        <button className="ghostButton" onClick={saveReport} disabled={busy || !canEditFinal(user)}>
                          <Save size={18} />
                          Сохранить
                        </button>
                        <button className="primaryButton" onClick={confirmReport} disabled={busy || !canEditFinal(user) || !finalText}>
                          <CheckCircle size={18} />
                          Подтвердить
                        </button>
                      </div>
                      <div className="buttonRow">
                        <button className="ghostButton" onClick={() => exportReport("pdf")} disabled={!report?.confirmed_at || busy}>
                          <Download size={18} />
                          PDF
                        </button>
                        <button className="ghostButton" onClick={() => exportReport("docx")} disabled={!report?.confirmed_at || busy}>
                          <Download size={18} />
                          Word
                        </button>
                      </div>
                      <small>Подтверждено: {formatDate(report?.confirmed_at)}</small>
                    </div>

                    <div className="toolPanel">
                      <div className="panelHeader">
                        <h2>Обратная связь</h2>
                        <Send size={20} />
                      </div>
                      <select value={feedbackType} onChange={(event) => setFeedbackType(event.target.value as FeedbackType)}>
                        {Object.entries(FEEDBACK_LABELS).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                      <textarea
                        value={feedbackComment}
                        onChange={(event) => setFeedbackComment(event.target.value)}
                        rows={4}
                        placeholder="Комментарий врача"
                      />
                      <button className="ghostButton" onClick={sendFeedback} disabled={busy || !latestAI}>
                        <Send size={18} />
                        Отправить
                      </button>
                    </div>
                  </section>
                </>
              ) : (
                <div className="emptyState large">Выберите исследование или загрузите новый снимок</div>
              )}
            </div>
          </section>
        )}

        {view === "reference" && (
          <section className="referenceGrid">
            {pathologies.map((item) => (
              <article className="referenceItem" key={item.id}>
                <h2>{item.title}</h2>
                <h3>Признаки</h3>
                <p>{item.signs}</p>
                <h3>Шаблон</h3>
                <p>{item.report_template}</p>
                {item.references && <small>{item.references}</small>}
              </article>
            ))}
          </section>
        )}

        {view === "analytics" && (
          <section className="analyticsGrid">
            <Metric title="Исследования" value={analytics?.studies_total ?? 0} />
            <Metric title="AI завершено" value={analytics?.ai_completed ?? 0} />
            <Metric title="AI ошибки" value={analytics?.ai_failed ?? 0} />
            <Metric title="Средний confidence" value={analytics?.ai_average_confidence ? formatPercent(analytics.ai_average_confidence) : "—"} />
            <div className="toolPanel wide">
              <h2>Статусы</h2>
              {Object.entries(analytics?.studies_by_status ?? {}).map(([status, count]) => (
                <div className="metricLine" key={status}>
                  <span>{STATUS_LABELS[status as StudyStatus] ?? status}</span>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
            <div className="toolPanel wide">
              <h2>Ошибки AI</h2>
              {Object.entries(analytics?.feedback_by_type ?? {}).map(([type, count]) => (
                <div className="metricLine" key={type}>
                  <span>{FEEDBACK_LABELS[type as FeedbackType] ?? type}</span>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          </section>
        )}

        {view === "audit" && (
          <section className="tablePanel">
            <table>
              <thead>
                <tr>
                  <th>Время</th>
                  <th>Пользователь</th>
                  <th>Действие</th>
                  <th>Сущность</th>
                  <th>Детали</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDate(row.created_at)}</td>
                    <td>{row.user?.login ?? "system"}</td>
                    <td>{row.action}</td>
                    <td>{row.entity_type ?? "—"} #{row.entity_id ?? "—"}</td>
                    <td>{row.details_json}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {view === "users" && (
          <section className="tablePanel">
            <table>
              <thead>
                <tr>
                  <th>Логин</th>
                  <th>ФИО</th>
                  <th>Роль</th>
                  <th>Активен</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td>{item.login}</td>
                    <td>{item.full_name}</td>
                    <td>{ROLE_LABELS[item.role]}</td>
                    <td>{item.is_active ? "да" : "нет"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
    </div>
  );
}

function NavButton({
  active,
  icon,
  label,
  onClick
}: {
  active: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={`navButton ${active ? "active" : ""}`} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}

function IconButton({
  active,
  children,
  label,
  onClick
}: {
  active?: boolean;
  children: ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button className={`iconButton ${active ? "active" : ""}`} title={label} aria-label={label} onClick={onClick}>
      {children}
    </button>
  );
}

function StatusBadge({ status }: { status: StudyStatus }) {
  return <span className={`statusBadge ${status}`}>{STATUS_LABELS[status]}</span>;
}

function Metric({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="metricCard">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}

function viewTitle(view: View) {
  const titles: Record<View, string> = {
    dashboard: "Исследования",
    reference: "Справочник патологий ОГК",
    analytics: "Аналитика",
    audit: "Журнал аудита",
    users: "Пользователи"
  };
  return titles[view];
}
