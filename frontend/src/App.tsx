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
  ImagePlus,
  Languages,
  Loader2,
  LogIn,
  LogOut,
  Moon,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Send,
  Stethoscope,
  Sun,
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
  CRMRecord,
  FeedbackType,
  Pathology,
  Report,
  Study,
  StudyStatus,
  User
} from "./types";

type View = "studies" | "crm" | "reference" | "analytics" | "audit" | "users";
type Lang = "kk" | "ru" | "en";
type Theme = "light" | "dark";

const UI = {
  kk: {
    locale: "kk-KZ",
    appName: "MedAI Radiology",
    appSubtitle: "Жергілікті AI-рентген талдау платформасы",
    loginTitle: "Клиникалық жұмыс орнына кіру",
    loginLead: "DICOM, PNG және JPEG суреттерін жергілікті MedAI арқылы талдап, дәрігерге арналған қорытынды жобасын жасаңыз.",
    login: "Логин",
    password: "Құпиясөз",
    signIn: "Кіру",
    unknownError: "Белгісіз қате",
    signedIn: "Жүйеге кірдіңіз",
    logout: "Шығу",
    refresh: "Жаңарту",
    nav: {
      overview: "Шолу",
      studies: "Зерттеулер",
      crm: "CRM",
      reference: "Анықтамалық",
      analytics: "Аналитика",
      audit: "Аудит",
      users: "Қолданушылар"
    },
    titles: {
      overview: "Платформа шолуы",
      studies: "Зерттеулер",
      crm: "Пациент CRM",
      reference: "Кеуде патологиялары",
      analytics: "Аналитика",
      audit: "Аудит журналы",
      users: "Қолданушылар"
    },
    roles: {
      admin: "Әкімші",
      radiologist: "Рентгенолог",
      physician: "Дәрігер",
      expert: "Сарапшы",
      student: "Студент",
      analyst: "Аналитик"
    },
    statuses: {
      created: "құрылды",
      uploaded: "жүктелді",
      checked: "тексерілді",
      ready_for_analysis: "AI-ға дайын",
      analyzing: "талдануда",
      ai_completed: "AI дайын",
      draft_ready: "жоба дайын",
      confirmed: "расталды",
      exported: "экспортталды",
      failed: "қате"
    },
    findings: {
      normal: "Норма",
      pneumonia: "Пневмония",
      pleural_effusion: "Плевралық сұйықтық",
      pneumothorax: "Пневмоторакс",
      atelectasis: "Ателектаз"
    },
    feedback: {
      false_positive: "Жалған оң",
      false_negative: "Жалған теріс",
      wrong_region: "Аймақ қате",
      other: "Басқа"
    },
    overviewHeroTitle: "Жергілікті MedAI негізіндегі радиология ассистенті",
    overviewHeroText:
      "Платформа зерттеуді қабылдайды, суретті тексереді, клиникалық жазбамен бірге AI талдау жасайды, қорытынды жобасын дайындайды және PDF/Word экспортын береді. Деректер локалды компьютерде қалады.",
    startStudy: "Жаңа зерттеу",
    openReference: "Анықтамалық",
    localModel: "Жергілікті AI",
    modelValue: "AI",
    privacy: "Жеке режим",
    privacyValue: "Сыртқы API жоқ",
    workflow: "Жұмыс барысы",
    workflowItems: [
      "Зерттеу ашылады және сурет жүктеледі.",
      "DICOM/JPEG/PNG файлы тексеріліп, preview жасалады.",
      "MedAI сурет пен клиникалық жазбаны бірге талдайды.",
      "Дәрігер AI жобасын тексеріп, финал мәтінді растайды.",
      "Жүйе мөрі, суреті және қол қою аймағы бар PDF/Word жасалады."
    ],
    capabilities: "Мүмкіндіктер",
    crmTitle: "Қолмен жазылатын CRM",
    crmSubtitle: "Пациент байланысы, ескертпе және келесі әрекеттер",
    crmSummary: "Қысқаша",
    crmNote: "Қолмен жазба",
    crmNextStep: "Келесі қадам",
    crmContact: "Байланыс түрі",
    crmPriority: "Маңыздылық",
    crmDue: "Күні",
    crmSave: "CRM жазбасын сақтау",
    crmEmpty: "Қолмен жазылған CRM жазбалары жоқ",
    crmSaved: "CRM жазбасы сақталды",
    crmActive: "Белсенді",
    crmFollowUp: "Бақылау",
    crmClosed: "Жабық",
    crmNormal: "Қалыпты",
    crmHigh: "Жоғары",
    crmUrgent: "Шұғыл",
    newStudy: "Жаңа зерттеу",
    patientCode: "Пациент коды",
    studyType: "Түрі",
    clinicalNote: "Клиникалық жазба",
    uploadLabel: "DICOM / JPEG / PNG",
    autoAI: "Жүктегеннен кейін AI",
    createUpload: "Құру және жүктеу",
    chooseFile: "DICOM, JPEG немесе PNG таңдаңыз",
    uploadedAI: "Файл жүктелді, AI талдау аяқталды",
    uploaded: "Файл жүктелді және тексерілді",
    filters: "Сүзгілер",
    allStatuses: "Барлық статустар",
    type: "Түрі",
    apply: "Қолдану",
    emptyStudies: "Таңдалған сүзгілер бойынша зерттеу жоқ",
    selectStudy: "Зерттеуді таңдаңыз немесе жаңа сурет жүктеңіз",
    brightness: "Жарықтық",
    contrast: "Контраст",
    zoomIn: "Үлкейту",
    zoomOut: "Кішірейту",
    reset: "Қалпына келтіру",
    previewMissing: "Preview қолжетімсіз",
    aiAnalysis: "AI талдау",
    disclaimer: "AI нәтижесі алдын ала көмек. Соңғы шешімді тек дәрігер қабылдайды.",
    runAI: "AI іске қосу",
    aiDone: "AI талдау аяқталды",
    aiFailed: "AI талдау орындалмады",
    status: "Статус",
    confidence: "Сенімділік",
    threshold: "Шек",
    model: "AI",
    dataset: "Дерек",
    classUnknown: "Класс анықталмады",
    lowConfidenceWarning: "AI сенімділігі төмен. Нәтижені дәрігер қолмен тексеруі керек.",
    createDraft: "Жоба жасау",
    draftDone: "AI жоба жасалды",
    report: "Қорытынды",
    aiDraft: "AI жоба",
    finalText: "Дәрігердің финал мәтіні",
    save: "Сақтау",
    saved: "Финал мәтін сақталды",
    confirm: "Растау",
    confirmed: "Қорытынды расталды",
    exported: "Экспорт дайын",
    confirmedAt: "Расталған уақыты",
    feedbackTitle: "Кері байланыс",
    feedbackComment: "Дәрігер пікірі",
    send: "Жіберу",
    feedbackSaved: "Кері байланыс сақталды",
    aiWaiting: "MedAI талдап жатыр",
    aiWaitingSub: "Сурет пен клиникалық жазба жергілікті AI жүйесіне жіберілді. Бірінші жауап бірнеше секундқа созылуы мүмкін.",
    noData: "дерек жоқ",
    myLungs: "Өкпе талдауы",
    lungsCondition: "Өкпе жағдайы",
    pulmonologyWorkspace: "Пульмонология жұмыс орны",
    aiReady: "AI дайын",
    reportsReady: "Қорытынды",
    crmNotes: "CRM жазбалары",
    readingTeam: "Дәрігерлер",
    scheduleTitle: "Оқу кестесі",
    nextChestCheck: "Келесі CXR тексеруі",
    noStudies: "Зерттеу жоқ",
    leadReader: "Жетекші",
    consultNow: "Кеңес ашу",
    chestViews: "Кеуде көріністері",
    frontalCxr: "Фронталды CXR",
    lateralCxr: "Бүйір CXR / CT",
    pdfWordExport: "PDF / Word экспорт",
    localLora: "Локалды LoRA",
    searchPlaceholder: "Іздеу...",
    heatmap: "Heatmap",
    homeBadge: "Локалды AI көмекшісі кеуде зерттеулеріне арналған",
    homeTitle: "MedAI кеуде снимогын тез талдайды",
    homeText: "Суретті жүктеңіз, AI қорытынды жобасын алыңыз және дәрігерлік тексеруге дайын жұмыс орнында зерттеуді жүргізіңіз.",
    homePrimary: "Зерттеуді бастау",
    homeSecondary: "Справочник ашу",
    homeCardTitle: "Chest AI",
    homeCardText: "CXR, DICOM, JPEG және PNG үшін локалды талдау.",
    homeFeatureOne: "AI талдау",
    homeFeatureTwo: "Қорытынды",
    homeFeatureThree: "Локалды дерек"
  },
  ru: {
    locale: "ru-RU",
    appName: "MedAI Radiology",
    appSubtitle: "Локальная AI-платформа анализа рентген-снимков",
    loginTitle: "Вход в клиническое рабочее место",
    loginLead: "Анализируйте DICOM, PNG и JPEG через локальную MedAI и формируйте черновики заключений для врача.",
    login: "Логин",
    password: "Пароль",
    signIn: "Войти",
    unknownError: "Неизвестная ошибка",
    signedIn: "Вход выполнен",
    logout: "Выйти",
    refresh: "Обновить",
    nav: {
      overview: "Обзор",
      studies: "Исследования",
      crm: "CRM",
      reference: "Справочник",
      analytics: "Аналитика",
      audit: "Аудит",
      users: "Пользователи"
    },
    titles: {
      overview: "Обзор платформы",
      studies: "Исследования",
      crm: "Пациент CRM",
      reference: "Патологии ОГК",
      analytics: "Аналитика",
      audit: "Журнал аудита",
      users: "Пользователи"
    },
    roles: {
      admin: "Администратор",
      radiologist: "Рентгенолог",
      physician: "Врач",
      expert: "Эксперт",
      student: "Студент",
      analyst: "Аналитик"
    },
    statuses: {
      created: "создано",
      uploaded: "загружено",
      checked: "проверено",
      ready_for_analysis: "готово к AI",
      analyzing: "анализируется",
      ai_completed: "AI готов",
      draft_ready: "черновик готов",
      confirmed: "подтверждено",
      exported: "экспортировано",
      failed: "ошибка"
    },
    findings: {
      normal: "Норма",
      pneumonia: "Пневмония",
      pleural_effusion: "Плевральный выпот",
      pneumothorax: "Пневмоторакс",
      atelectasis: "Ателектаз"
    },
    feedback: {
      false_positive: "Ложно положительный",
      false_negative: "Ложно отрицательный",
      wrong_region: "Неверная зона",
      other: "Другое"
    },
    overviewHeroTitle: "Радиологический ассистент MedAI",
    overviewHeroText:
      "Платформа принимает исследование, проверяет снимок, анализирует изображение вместе с клинической заметкой, готовит черновик заключения и экспортирует PDF/Word. Данные остаются на локальном компьютере.",
    startStudy: "Новое исследование",
    openReference: "Справочник",
    localModel: "Локальный AI",
    modelValue: "AI",
    privacy: "Приватный режим",
    privacyValue: "Без внешнего API",
    workflow: "Рабочий процесс",
    workflowItems: [
      "Создается исследование и загружается снимок.",
      "DICOM/JPEG/PNG проверяется и получает preview.",
      "MedAI анализирует снимок вместе с клинической заметкой.",
      "Врач проверяет AI-черновик и подтверждает финальный текст.",
      "Система экспортирует PDF/Word с печатью, снимком и зоной подписи."
    ],
    capabilities: "Возможности",
    crmTitle: "Ручная CRM",
    crmSubtitle: "Контакты пациента, заметки и следующие действия",
    crmSummary: "Кратко",
    crmNote: "Ручная запись",
    crmNextStep: "Следующий шаг",
    crmContact: "Тип контакта",
    crmPriority: "Приоритет",
    crmDue: "Дата",
    crmSave: "Сохранить CRM запись",
    crmEmpty: "Ручных CRM записей пока нет",
    crmSaved: "CRM запись сохранена",
    crmActive: "Активно",
    crmFollowUp: "Контроль",
    crmClosed: "Закрыто",
    crmNormal: "Обычный",
    crmHigh: "Высокий",
    crmUrgent: "Срочно",
    newStudy: "Новое исследование",
    patientCode: "Код пациента",
    studyType: "Тип",
    clinicalNote: "Клиническая заметка",
    uploadLabel: "DICOM / JPEG / PNG",
    autoAI: "Авто AI после загрузки",
    createUpload: "Создать и загрузить",
    chooseFile: "Выберите DICOM, JPEG или PNG",
    uploadedAI: "Файл загружен, AI-анализ выполнен",
    uploaded: "Файл загружен и проверен",
    filters: "Фильтры",
    allStatuses: "Все статусы",
    type: "Тип",
    apply: "Применить",
    emptyStudies: "Нет исследований для выбранных фильтров",
    selectStudy: "Выберите исследование или загрузите новый снимок",
    brightness: "Яркость",
    contrast: "Контраст",
    zoomIn: "Увеличить",
    zoomOut: "Уменьшить",
    reset: "Сбросить",
    previewMissing: "Preview пока недоступно",
    aiAnalysis: "AI-анализ",
    disclaimer: "Результат AI является предварительной подсказкой. Окончательное решение принимает врач.",
    runAI: "Запустить AI",
    aiDone: "AI-анализ завершен",
    aiFailed: "AI-анализ не выполнен",
    status: "Статус",
    confidence: "Уверенность",
    threshold: "Порог",
    model: "AI",
    dataset: "Данные",
    classUnknown: "Класс не определен",
    lowConfidenceWarning: "Уверенность AI низкая. Результат должен быть проверен врачом вручную.",
    createDraft: "Создать черновик",
    draftDone: "AI-черновик создан",
    report: "Заключение",
    aiDraft: "AI-черновик",
    finalText: "Финальный текст врача",
    save: "Сохранить",
    saved: "Финальный текст сохранен",
    confirm: "Подтвердить",
    confirmed: "Заключение подтверждено",
    exported: "Экспорт готов",
    confirmedAt: "Подтверждено",
    feedbackTitle: "Обратная связь",
    feedbackComment: "Комментарий врача",
    send: "Отправить",
    feedbackSaved: "Обратная связь сохранена",
    aiWaiting: "MedAI анализирует",
    aiWaitingSub: "Снимок и клиническая заметка отправлены в локальный AI. Первый ответ может занять несколько секунд.",
    noData: "нет данных",
    myLungs: "Мои легкие",
    lungsCondition: "Состояние легких",
    pulmonologyWorkspace: "Пульмонология ОГК",
    aiReady: "Готово к AI",
    reportsReady: "Заключения",
    crmNotes: "CRM заметки",
    readingTeam: "Врачи",
    scheduleTitle: "График чтения",
    nextChestCheck: "Следующий CXR-контроль",
    noStudies: "Нет исследований",
    leadReader: "Ведущий",
    consultNow: "Открыть консультацию",
    chestViews: "Проекции грудной клетки",
    frontalCxr: "Фронтальный CXR",
    lateralCxr: "Боковой CXR / CT",
    pdfWordExport: "PDF / Word экспорт",
    localLora: "Локальная LoRA",
    searchPlaceholder: "Поиск...",
    heatmap: "Теплокарта",
    homeBadge: "Локальный AI-ассистент для исследований грудной клетки",
    homeTitle: "MedAI помогает разбирать снимки ОГК",
    homeText: "Загрузите снимок, получите AI-черновик заключения и ведите исследование в аккуратном рабочем пространстве врача.",
    homePrimary: "Начать исследование",
    homeSecondary: "Открыть справочник",
    homeCardTitle: "Chest AI",
    homeCardText: "Локальный анализ CXR, DICOM, JPEG и PNG.",
    homeFeatureOne: "AI-анализ",
    homeFeatureTwo: "Заключение",
    homeFeatureThree: "Локальные данные"
  },
  en: {
    locale: "en-US",
    appName: "MedAI Radiology",
    appSubtitle: "Local AI chest imaging workspace",
    loginTitle: "Sign in to the clinical workspace",
    loginLead: "Analyze DICOM, PNG and JPEG images with local MedAI and prepare clinician-reviewed report drafts.",
    login: "Login",
    password: "Password",
    signIn: "Sign in",
    unknownError: "Unknown error",
    signedIn: "Signed in",
    logout: "Log out",
    refresh: "Refresh",
    nav: {
      overview: "Overview",
      studies: "Studies",
      crm: "CRM",
      reference: "Reference",
      analytics: "Analytics",
      audit: "Audit",
      users: "Users"
    },
    titles: {
      overview: "Platform overview",
      studies: "Studies",
      crm: "Patient CRM",
      reference: "Chest pathology reference",
      analytics: "Analytics",
      audit: "Audit log",
      users: "Users"
    },
    roles: {
      admin: "Administrator",
      radiologist: "Radiologist",
      physician: "Physician",
      expert: "Expert",
      student: "Student",
      analyst: "Analyst"
    },
    statuses: {
      created: "created",
      uploaded: "uploaded",
      checked: "checked",
      ready_for_analysis: "ready for AI",
      analyzing: "analyzing",
      ai_completed: "AI complete",
      draft_ready: "draft ready",
      confirmed: "confirmed",
      exported: "exported",
      failed: "failed"
    },
    findings: {
      normal: "Normal",
      pneumonia: "Pneumonia",
      pleural_effusion: "Pleural effusion",
      pneumothorax: "Pneumothorax",
      atelectasis: "Atelectasis"
    },
    feedback: {
      false_positive: "False positive",
      false_negative: "False negative",
      wrong_region: "Wrong region",
      other: "Other"
    },
    overviewHeroTitle: "Local MedAI radiology assistant",
    overviewHeroText:
      "The platform receives a study, validates the image, analyzes it together with clinical notes, prepares a report draft, and exports PDF/Word. Data stays on this computer.",
    startStudy: "New study",
    openReference: "Reference",
    localModel: "Local AI",
    modelValue: "AI",
    privacy: "Private mode",
    privacyValue: "No external API",
    workflow: "Workflow",
    workflowItems: [
      "Create a study and upload an image.",
      "DICOM/JPEG/PNG is validated and previewed.",
      "MedAI analyzes the image with the clinical note.",
      "The clinician reviews the AI draft and confirms the final text.",
      "The system exports PDF/Word with stamp, image and signature area."
    ],
    capabilities: "Capabilities",
    crmTitle: "Manual CRM",
    crmSubtitle: "Patient contacts, notes and next actions",
    crmSummary: "Summary",
    crmNote: "Manual note",
    crmNextStep: "Next step",
    crmContact: "Contact type",
    crmPriority: "Priority",
    crmDue: "Date",
    crmSave: "Save CRM record",
    crmEmpty: "No manual CRM records yet",
    crmSaved: "CRM record saved",
    crmActive: "Active",
    crmFollowUp: "Follow-up",
    crmClosed: "Closed",
    crmNormal: "Normal",
    crmHigh: "High",
    crmUrgent: "Urgent",
    newStudy: "New study",
    patientCode: "Patient code",
    studyType: "Type",
    clinicalNote: "Clinical note",
    uploadLabel: "DICOM / JPEG / PNG",
    autoAI: "Auto AI after upload",
    createUpload: "Create and upload",
    chooseFile: "Choose a DICOM, JPEG or PNG file",
    uploadedAI: "File uploaded, AI analysis complete",
    uploaded: "File uploaded and validated",
    filters: "Filters",
    allStatuses: "All statuses",
    type: "Type",
    apply: "Apply",
    emptyStudies: "No studies for selected filters",
    selectStudy: "Select a study or upload a new image",
    brightness: "Brightness",
    contrast: "Contrast",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    reset: "Reset",
    previewMissing: "Preview is not available yet",
    aiAnalysis: "AI analysis",
    disclaimer: "AI output is preliminary decision support. The final decision belongs to the clinician.",
    runAI: "Run AI",
    aiDone: "AI analysis complete",
    aiFailed: "AI analysis failed",
    status: "Status",
    confidence: "Confidence",
    threshold: "Threshold",
    model: "AI",
    dataset: "Data",
    classUnknown: "Class not defined",
    lowConfidenceWarning: "AI confidence is low. The result must be checked manually by a clinician.",
    createDraft: "Create draft",
    draftDone: "AI draft created",
    report: "Report",
    aiDraft: "AI draft",
    finalText: "Clinician final text",
    save: "Save",
    saved: "Final text saved",
    confirm: "Confirm",
    confirmed: "Report confirmed",
    exported: "Export ready",
    confirmedAt: "Confirmed",
    feedbackTitle: "Feedback",
    feedbackComment: "Clinician comment",
    send: "Send",
    feedbackSaved: "Feedback saved",
    aiWaiting: "MedAI is analyzing",
    aiWaitingSub: "The image and clinical note were sent to the local AI. The first response can take a few seconds.",
    noData: "no data",
    myLungs: "My Lungs",
    lungsCondition: "Lungs Status",
    pulmonologyWorkspace: "Pulmonology Workspace",
    aiReady: "AI Ready",
    reportsReady: "Reports",
    crmNotes: "CRM Notes",
    readingTeam: "Reading Team",
    scheduleTitle: "Reading Schedule",
    nextChestCheck: "Next CXR Check",
    noStudies: "No studies",
    leadReader: "Lead",
    consultNow: "Open Consult",
    chestViews: "Chest Views",
    frontalCxr: "Frontal PA CXR",
    lateralCxr: "Lateral CXR / CT",
    pdfWordExport: "PDF / Word Export",
    localLora: "Local LoRA",
    searchPlaceholder: "Search...",
    heatmap: "Heatmap",
    homeBadge: "Local AI assistant for chest imaging",
    homeTitle: "MedAI helps read chest studies",
    homeText: "Upload an image, get an AI report draft, and review the study in a clean clinician workspace.",
    homePrimary: "Start study",
    homeSecondary: "Open reference",
    homeCardTitle: "Chest AI",
    homeCardText: "Local analysis for CXR, DICOM, JPEG and PNG.",
    homeFeatureOne: "AI analysis",
    homeFeatureTwo: "Report draft",
    homeFeatureThree: "Local data"
  }
} as const;

function formatDate(value: string | null | undefined, lang: Lang) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(UI[lang].locale, {
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
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem("medicine_lang") as Lang) || "kk");
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("medicine_theme") as Theme) || "light");
  const ui = UI[lang];

  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [view, setView] = useState<View>("studies");
  const [showLoginPanel, setShowLoginPanel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [aiRunningStudyId, setAiRunningStudyId] = useState<number | null>(null);
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
  const [doctors, setDoctors] = useState<User[]>([]);
  const [crmRecords, setCrmRecords] = useState<CRMRecord[]>([]);
  const [crmForm, setCrmForm] = useState({
    patient_code: "DEMO-001",
    contact_type: "consultation",
    status: "active",
    priority: "normal",
    summary: "",
    note: "",
    next_step: "",
    due_at: ""
  });

  const [filters, setFilters] = useState({ status: "", study_type: "", date_from: "", date_to: "" });
  const [newStudy, setNewStudy] = useState({ patient_code: "DEMO-001", study_type: "CXR", clinical_note: "" });
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
  const selectedStudyAiBusy = Boolean(selectedStudy && aiRunningStudyId === selectedStudy.id);
  const probabilityRows = useMemo(() => parseProbabilities(latestAI?.probabilities_json ?? null), [latestAI]);

  useEffect(() => {
    localStorage.setItem("medicine_lang", lang);
  }, [lang]);

  useEffect(() => {
    localStorage.setItem("medicine_theme", theme);
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 3200);
    return () => window.clearTimeout(timer);
  }, [notice]);

  useEffect(() => {
    async function restore() {
      if (!currentToken()) {
        setBooting(false);
        return;
      }
      try {
        const me = await api.me();
        setUser(me);
        setView("studies");
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
    await Promise.all([loadStudies(), loadPathologies(), loadDoctors(), loadCrm()]);
    if (nextUser && ["admin", "analyst", "expert"].includes(nextUser.role)) {
      await loadAnalytics();
    }
  }

  function flash(message: string) {
    setNotice(message);
    setError("");
  }

  function fail(err: unknown) {
    setError(err instanceof Error ? err.message : ui.unknownError);
    setNotice("");
  }

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      const response = await api.login(login, password);
      setAuthToken(response.access_token);
      setUser(response.user);
      setView("studies");
      setShowLoginPanel(false);
      await loadInitial(response.user);
      flash(ui.signedIn);
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
    setCrmRecords([]);
    setDoctors([]);
    setPreviewUrl(null);
    setShowLoginPanel(false);
    setView("studies");
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

  async function loadDoctors() {
    const data = await api.listDoctors();
    setDoctors(data);
  }

  async function loadCrm() {
    const data = await api.listCrm();
    setCrmRecords(data);
  }

  async function saveCrmRecord(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.createCrm({
        ...crmForm,
        next_step: crmForm.next_step || null,
        due_at: crmForm.due_at ? new Date(crmForm.due_at).toISOString() : null
      });
      setCrmForm({
        patient_code: crmForm.patient_code,
        contact_type: "consultation",
        status: "active",
        priority: "normal",
        summary: "",
        note: "",
        next_step: "",
        due_at: ""
      });
      await loadCrm();
      flash(ui.crmSaved);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function openStudy(studyId: number) {
    setBusy(true);
    try {
      const detail = await api.getStudy(studyId);
      setSelectedStudy(detail);
      setView("studies");
      setAiResults(await api.listAI(studyId));
      await loadPreview(studyId);
      try {
        const nextReport = await api.getReport(studyId);
        setReport(nextReport);
        setFinalText(nextReport.final_text || nextReport.ai_draft_text || "");
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
      setError(ui.chooseFile);
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
        setAiRunningStudyId(uploaded.id);
        try {
          analysis = await api.runAI(uploaded.id, true, true, lang);
          setAiResults([analysis]);
          if (analysis.status === "failed") {
            throw new Error(analysis.error_message || ui.aiFailed);
          }
          const draft = await api.createDraft(uploaded.id, lang);
          setReport(draft);
          setFinalText(draft.ai_draft_text || draft.final_text || "");
        } finally {
          setAiRunningStudyId(null);
        }
      }
      setSelectedStudy(await api.getStudy(uploaded.id));
      await loadStudies();
      flash(analysis ? ui.uploadedAI : ui.uploaded);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function runAI(auto = false) {
    if (!selectedStudy) return;
    setBusy(true);
    setAiRunningStudyId(selectedStudy.id);
    try {
      const analysis = await api.runAI(selectedStudy.id, true, auto, lang);
      setAiResults([analysis]);
      if (analysis.status === "failed") {
        throw new Error(analysis.error_message || ui.aiFailed);
      }
      if (analysis.status === "completed") {
        const nextReport = await api.createDraft(selectedStudy.id, lang);
        setReport(nextReport);
        setFinalText(nextReport.ai_draft_text || nextReport.final_text || "");
      }
      const detail = await api.getStudy(selectedStudy.id);
      setSelectedStudy(detail);
      await loadStudies();
      flash(ui.aiDone);
    } catch (err) {
      fail(err);
    } finally {
      setAiRunningStudyId(null);
      setBusy(false);
    }
  }

  async function createDraft() {
    if (!selectedStudy) return;
    setBusy(true);
    try {
      const nextReport = await api.createDraft(selectedStudy.id, lang);
      setReport(nextReport);
      setFinalText(nextReport.ai_draft_text || nextReport.final_text || "");
      setSelectedStudy(await api.getStudy(selectedStudy.id));
      await loadStudies();
      flash(ui.draftDone);
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
      flash(ui.saved);
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
      flash(ui.confirmed);
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
      const blob = await api.exportReport(selectedStudy.id, format, lang);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${selectedStudy.accession_number}.${format}`;
      anchor.click();
      URL.revokeObjectURL(url);
      await loadStudies();
      flash(`${ui.exported}: ${format.toUpperCase()}`);
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
      flash(ui.feedbackSaved);
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
    return (
      <div className="boot">
        <div className="pulseLoader">
          <Stethoscope size={30} />
        </div>
        <strong>{ui.appName}</strong>
      </div>
    );
  }

  if (!user) {
    return (
      <main className="publicShell">
        <header className="publicHeader">
          <span className="photonBrand">MedAI</span>
          <div className="headerControls">
            <ThemeSwitch theme={theme} setTheme={setTheme} />
            <LanguageSwitch lang={lang} setLang={setLang} />
            <button className="loginTopButton" type="button" onClick={() => setShowLoginPanel(true)}>
              <LogIn size={18} />
              {ui.signIn}
            </button>
          </div>
        </header>

        <section className="photonDashboard overviewScene publicOverview">
          <div className="photonCopy dashboardCopy">
            <h1>
              <span>Chest</span>
              <span>
                Radiology <b>A.I.</b>
              </span>
            </h1>
            <div className="photonMeta">
              <span>Local MedAI</span>
              <i />
              <span>2026</span>
            </div>
            <div className="photonActionRow">
              <button className="photonRoundButton" type="button" onClick={() => setShowLoginPanel(true)} aria-label={ui.signIn}>
                <Play size={18} />
              </button>
              <span>Start local chest AI workflow</span>
            </div>
            <p className="photonNote">
              MedAI is a local radiology workspace for chest imaging, AI draft reports, and clinician review.
            </p>
          </div>

          <div className="photonVisual dashboardVisual" aria-hidden="true">
            <img src="/neon_lungs_hero_transparent.png" alt="" />
          </div>

          <aside className="photonSide dashboardSide">
            <p>
              <strong>{ui.localModel}</strong>
            </p>
            <span />
            <p>Chest AI for local reports, studies, and reference review.</p>
          </aside>

          <footer className="photonFooter overviewFooter">
            <button type="button" onClick={() => setShowLoginPanel(true)}>{ui.homeFeatureThree}</button>
            <button type="button" onClick={() => setShowLoginPanel(true)}>{ui.homeFeatureOne}</button>
            <div />
            <button type="button" onClick={() => setShowLoginPanel(true)}>{ui.homeSecondary}</button>
            <button type="button" onClick={() => setShowLoginPanel(true)}>{ui.homePrimary}</button>
          </footer>
        </section>

        {showLoginPanel && (
          <div className="loginModalBackdrop" onMouseDown={() => setShowLoginPanel(false)}>
            <form className="loginPanel loginModal" onSubmit={handleLogin} onMouseDown={(event) => event.stopPropagation()}>
              <div className="modalHeader">
                <span>{ui.appName}</span>
                <button type="button" onClick={() => setShowLoginPanel(false)} aria-label="Close">×</button>
              </div>
              <h1>{ui.loginTitle}</h1>
              <p>{ui.loginLead}</p>
              <label>
                {ui.login}
                <input value={login} onChange={(event) => setLogin(event.target.value)} autoComplete="username" />
              </label>
              <label>
                {ui.password}
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
              </label>
              <button className="loginSubmit" disabled={busy}>
                <LogIn size={18} />
                {ui.signIn}
              </button>
              {error && <div className="errorLine">{error}</div>}
            </form>
          </div>
        )}
      </main>
    );
  }

  return (
    <div className="appShell">
      <aside className="sidebar">
        <div className="brand">
          <strong>MedAI</strong>
          <span>{ui.roles[user.role]}</span>
        </div>
        <nav>
          <NavButton active={view === "studies"} icon={<Activity size={18} />} label={ui.nav.studies} onClick={() => setView("studies")} />
          <NavButton
            active={view === "crm"}
            icon={<ClipboardList size={18} />}
            label={ui.nav.crm}
            onClick={async () => {
              setView("crm");
              await loadCrm();
            }}
          />
          <NavButton active={view === "reference"} icon={<BookOpen size={18} />} label={ui.nav.reference} onClick={() => setView("reference")} />
          {["admin", "analyst", "expert"].includes(user.role) && (
            <NavButton
              active={view === "analytics"}
              icon={<BarChart3 size={18} />}
              label={ui.nav.analytics}
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
              label={ui.nav.audit}
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
              label={ui.nav.users}
              onClick={async () => {
                setView("users");
                await loadUsers();
              }}
            />
          )}
        </nav>
        <label className="globalSearch">
          <input placeholder={ui.searchPlaceholder} />
          <Search size={18} />
        </label>
        <div className="sidebarFooter">
          <ThemeSwitch theme={theme} setTheme={setTheme} />
          <LanguageSwitch lang={lang} setLang={setLang} />
          <button className="ghostButton dark" onClick={logout}>
            <LogOut size={18} />
            {ui.logout}
          </button>
        </div>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <h1>{ui.titles[view]}</h1>
            <p>{user.full_name}</p>
          </div>
          <button className="ghostButton" onClick={() => loadInitial()} disabled={busy}>
            <RefreshCw size={18} />
            {ui.refresh}
          </button>
        </header>

        {notice && <div className="notice">{notice}</div>}
        {error && <div className="errorLine">{error}</div>}

        {view === "studies" && (
          <section className="dashboardGrid">
            <div className="leftColumn">
              {canUseClinicalFlow(user) && (
                <form className="toolPanel" onSubmit={createAndUpload}>
                  <div className="panelHeader">
                    <h2>{ui.newStudy}</h2>
                    <UploadCloud size={20} />
                  </div>
                  <div className="formGrid">
                    <label>
                      {ui.patientCode}
                      <input value={newStudy.patient_code} onChange={(event) => setNewStudy({ ...newStudy, patient_code: event.target.value })} />
                    </label>
                    <label>
                      {ui.studyType}
                      <select value={newStudy.study_type} onChange={(event) => setNewStudy({ ...newStudy, study_type: event.target.value })}>
                        <option value="CXR">CXR</option>
                        <option value="Chest X-ray">Chest X-ray</option>
                        <option value="ОГК">ОГК</option>
                      </select>
                    </label>
                  </div>
                  <label>
                    {ui.clinicalNote}
                    <textarea
                      value={newStudy.clinical_note}
                      onChange={(event) => setNewStudy({ ...newStudy, clinical_note: event.target.value })}
                      rows={3}
                    />
                  </label>
                  <label className="fileDrop">
                    <UploadCloud size={22} />
                    <span>{newFile ? newFile.name : ui.uploadLabel}</span>
                    <input
                      type="file"
                      accept=".dcm,.dicom,.jpg,.jpeg,.png,image/png,image/jpeg"
                      onChange={(event) => setNewFile(event.target.files?.[0] ?? null)}
                    />
                  </label>
                  <label className="checkLine">
                    <input type="checkbox" checked={autoAI} onChange={(event) => setAutoAI(event.target.checked)} />
                    {ui.autoAI}
                  </label>
                  <button className="primaryButton" disabled={busy}>
                    <Plus size={18} />
                    {ui.createUpload}
                  </button>
                </form>
              )}

              <div className="toolPanel">
                <div className="panelHeader">
                  <h2>{ui.filters}</h2>
                  <Search size={20} />
                </div>
                <div className="filterGrid">
                  <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
                    <option value="">{ui.allStatuses}</option>
                    {Object.entries(ui.statuses).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  <input placeholder={ui.type} value={filters.study_type} onChange={(event) => setFilters({ ...filters, study_type: event.target.value })} />
                  <input type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} />
                  <input type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} />
                </div>
                <button className="ghostButton" onClick={() => loadStudies()} disabled={busy}>
                  <Search size={18} />
                  {ui.apply}
                </button>
              </div>

              <div className="studyList">
                {studies.map((study) => (
                  <button
                    className={`studyRow ${selectedStudy?.id === study.id ? "active" : ""} ${aiRunningStudyId === study.id ? "processing" : ""}`}
                    key={study.id}
                    onClick={() => openStudy(study.id)}
                  >
                    <span>
                      <strong>{study.accession_number}</strong>
                      <small>{study.patient_code} · {study.study_type}</small>
                    </span>
                    {aiRunningStudyId === study.id ? (
                      <span className="studyProcessing">
                        <Loader2 size={14} />
                        AI
                      </span>
                    ) : (
                      <StatusBadge status={study.status} labels={ui.statuses} />
                    )}
                  </button>
                ))}
                {!studies.length && <div className="emptyState">{ui.emptyStudies}</div>}
              </div>
            </div>

            <div className="rightColumn">
              {selectedStudy ? (
                <>
                  <section className="viewerPanel">
                    <div className="panelHeader">
                      <div>
                        <h2>{selectedStudy.accession_number}</h2>
                        <p>{selectedStudy.patient_code} · {ui.statuses[selectedStudy.status]}</p>
                      </div>
                      <StatusBadge status={selectedStudy.status} labels={ui.statuses} />
                    </div>
                    <div className="viewerToolbar">
                      <IconButton label={ui.zoomIn} onClick={() => setZoom((value) => Math.min(value + 0.15, 3))}>
                        <ZoomIn size={18} />
                      </IconButton>
                      <IconButton label={ui.zoomOut} onClick={() => setZoom((value) => Math.max(value - 0.15, 0.4))}>
                        <ZoomOut size={18} />
                      </IconButton>
                      <IconButton label={ui.reset} onClick={resetViewer}>
                        <RotateCcw size={18} />
                      </IconButton>
                      <IconButton label={ui.heatmap} active={showHeatmap} onClick={() => setShowHeatmap((value) => !value)}>
                        <Eye size={18} />
                      </IconButton>
                      <label>
                        {ui.brightness}
                        <input type="range" min="50" max="160" value={brightness} onChange={(event) => setBrightness(Number(event.target.value))} />
                      </label>
                      <label>
                        {ui.contrast}
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
                            alt=""
                            style={{
                              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                              filter: `brightness(${brightness}%) contrast(${contrast}%)`
                            }}
                          />
                          {showHeatmap && <div className="heatmapOverlay" style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }} />}
                        </>
                      ) : (
                        <div className="emptyState">{ui.previewMissing}</div>
                      )}
                      {selectedStudyAiBusy && (
                        <div className="imageStageLoader">
                          <Loader2 size={24} />
                          <strong>{ui.aiWaiting}</strong>
                          <span>{selectedStudy.accession_number}</span>
                        </div>
                      )}
                    </div>
                  </section>

                  <section className="clinicalGrid">
                    <div className="toolPanel">
                      <div className="panelHeader">
                        <h2>{ui.aiAnalysis}</h2>
                        <Activity size={20} />
                      </div>
                      <div className="disclaimer">
                        <AlertTriangle size={18} />
                        <strong>{ui.disclaimer}</strong>
                      </div>
                      {selectedStudyAiBusy && (
                        <div className="inlineAiStatus">
                          <Loader2 size={18} />
                          <span>{ui.aiWaiting}</span>
                        </div>
                      )}
                      <button className="primaryButton" onClick={() => runAI(false)} disabled={busy || selectedStudyAiBusy}>
                        {selectedStudyAiBusy ? <Loader2 size={18} className="spinIcon" /> : <Play size={18} />}
                        {selectedStudyAiBusy ? ui.aiWaiting : ui.runAI}
                      </button>
                      {latestAI && (
                        <div className="aiResult">
                          <div className="metricLine">
                            <span>{ui.status}</span>
                            <strong>{latestAI.status}</strong>
                          </div>
                          {latestAI.hidden_due_low_confidence ? (
                            <div className="warningBox">{ui.lowConfidenceWarning}</div>
                          ) : (
                            <div className="prediction">
                              {latestAI.predicted_class ? ui.findings[latestAI.predicted_class] : ui.classUnknown}
                            </div>
                          )}
                          <div className="metricLine">
                            <span>{ui.confidence}</span>
                            <strong>{formatPercent(latestAI.confidence)}</strong>
                          </div>
                          <div className="metricLine">
                            <span>{ui.threshold}</span>
                            <strong>{formatPercent(latestAI.threshold)}</strong>
                          </div>
                          <div className="probabilityList">
                            {probabilityRows.map(([label, score]) => (
                              <div key={label}>
                                <span>{ui.findings[label as keyof typeof ui.findings] ?? label}</span>
                                <meter min={0} max={1} value={score} />
                                <b>{formatPercent(score)}</b>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                      <button className="ghostButton" onClick={createDraft} disabled={busy || !latestAI}>
                        <FileText size={18} />
                        {ui.createDraft}
                      </button>
                    </div>

                    <div className="toolPanel reportPanel">
                      <div className="panelHeader">
                        <h2>{ui.report}</h2>
                        <FileText size={20} />
                      </div>
                      <label>
                        {ui.aiDraft}
                        <textarea value={report?.ai_draft_text ?? ""} readOnly rows={8} />
                      </label>
                      <label>
                        {ui.finalText}
                        <textarea value={finalText} onChange={(event) => setFinalText(event.target.value)} readOnly={!canEditFinal(user)} rows={9} />
                      </label>
                      <div className="buttonRow">
                        <button className="ghostButton" onClick={saveReport} disabled={busy || !canEditFinal(user)}>
                          <Save size={18} />
                          {ui.save}
                        </button>
                        <button className="primaryButton" onClick={confirmReport} disabled={busy || !canEditFinal(user) || !finalText}>
                          <CheckCircle size={18} />
                          {ui.confirm}
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
                      <small>{ui.confirmedAt}: {formatDate(report?.confirmed_at, lang)}</small>
                    </div>

                    <div className="toolPanel">
                      <div className="panelHeader">
                        <h2>{ui.feedbackTitle}</h2>
                        <Send size={20} />
                      </div>
                      <select value={feedbackType} onChange={(event) => setFeedbackType(event.target.value as FeedbackType)}>
                        {Object.entries(ui.feedback).map(([value, label]) => (
                          <option key={value} value={value}>
                            {label}
                          </option>
                        ))}
                      </select>
                      <textarea value={feedbackComment} onChange={(event) => setFeedbackComment(event.target.value)} rows={4} placeholder={ui.feedbackComment} />
                      <button className="ghostButton" onClick={sendFeedback} disabled={busy || !latestAI}>
                        <Send size={18} />
                        {ui.send}
                      </button>
                    </div>
                  </section>
                </>
              ) : (
                <div className="emptyState large visualEmpty studyVisualEmpty">
                  <img src="/medical_lungs_xray.png" alt="" />
                  <span>{ui.selectStudy}</span>
                </div>
              )}
            </div>
          </section>
        )}

        {view === "crm" && (
          <section className="crmDashboard">
            <div className="crmHero">
              <div>
                <span>{ui.crmSubtitle}</span>
                <h2>{ui.crmTitle}</h2>
              </div>
              <div className="crmVitals">
                <div>
                  <strong>{crmRecords.filter((record) => record.status === "active").length}</strong>
                  <span>{ui.crmActive}</span>
                </div>
                <div>
                  <strong>{crmRecords.filter((record) => record.status === "follow_up").length}</strong>
                  <span>{ui.crmFollowUp}</span>
                </div>
                <div>
                  <strong>{crmRecords.filter((record) => record.priority === "urgent").length}</strong>
                  <span>{ui.crmUrgent}</span>
                </div>
              </div>
            </div>

            <form className="crmComposer" onSubmit={saveCrmRecord}>
              <div className="panelHeader">
                <h2>{ui.crmSave}</h2>
                <ClipboardList size={20} />
              </div>
              <div className="crmFormGrid">
                <label>
                  {ui.patientCode}
                  <input value={crmForm.patient_code} onChange={(event) => setCrmForm({ ...crmForm, patient_code: event.target.value })} />
                </label>
                <label>
                  {ui.crmContact}
                  <select value={crmForm.contact_type} onChange={(event) => setCrmForm({ ...crmForm, contact_type: event.target.value })}>
                    <option value="consultation">Consultation</option>
                    <option value="call">Call</option>
                    <option value="follow_up">Follow-up</option>
                    <option value="report">Report</option>
                  </select>
                </label>
                <label>
                  {ui.status}
                  <select value={crmForm.status} onChange={(event) => setCrmForm({ ...crmForm, status: event.target.value })}>
                    <option value="active">{ui.crmActive}</option>
                    <option value="follow_up">{ui.crmFollowUp}</option>
                    <option value="closed">{ui.crmClosed}</option>
                  </select>
                </label>
                <label>
                  {ui.crmPriority}
                  <select value={crmForm.priority} onChange={(event) => setCrmForm({ ...crmForm, priority: event.target.value })}>
                    <option value="normal">{ui.crmNormal}</option>
                    <option value="high">{ui.crmHigh}</option>
                    <option value="urgent">{ui.crmUrgent}</option>
                  </select>
                </label>
              </div>
              <label>
                {ui.crmSummary}
                <input value={crmForm.summary} onChange={(event) => setCrmForm({ ...crmForm, summary: event.target.value })} />
              </label>
              <label>
                {ui.crmNote}
                <textarea value={crmForm.note} onChange={(event) => setCrmForm({ ...crmForm, note: event.target.value })} rows={6} />
              </label>
              <div className="crmFormGrid two">
                <label>
                  {ui.crmNextStep}
                  <input value={crmForm.next_step} onChange={(event) => setCrmForm({ ...crmForm, next_step: event.target.value })} />
                </label>
                <label>
                  {ui.crmDue}
                  <input type="datetime-local" value={crmForm.due_at} onChange={(event) => setCrmForm({ ...crmForm, due_at: event.target.value })} />
                </label>
              </div>
              <button className="primaryButton" disabled={busy || !crmForm.patient_code || !crmForm.summary || !crmForm.note}>
                <Save size={18} />
                {ui.crmSave}
              </button>
            </form>

            <div className="crmBoard">
              {crmRecords.length === 0 && (
                <div className="emptyState large visualEmpty crmVisualEmpty">
                  <img src="/medical_lungs_xray.png" alt="" />
                  <span>{ui.crmEmpty}</span>
                </div>
              )}
              {crmRecords.map((record) => (
                <article className={`crmCard ${record.priority}`} key={record.id}>
                  <div className="crmCardTop">
                    <span>{record.patient_code}</span>
                    <b>{record.priority === "urgent" ? ui.crmUrgent : record.priority === "high" ? ui.crmHigh : ui.crmNormal}</b>
                  </div>
                  <h3>{record.summary}</h3>
                  <p>{record.note}</p>
                  <div className="crmCardMeta">
                    <span>{record.status === "follow_up" ? ui.crmFollowUp : record.status === "closed" ? ui.crmClosed : ui.crmActive}</span>
                    <span>{record.next_step || "—"}</span>
                    <span>{formatDate(record.due_at || record.updated_at, lang)}</span>
                  </div>
                  <div className="crmCardFooter">
                    <small>{record.created_by.full_name}</small>
                    <button
                      className="iconButton"
                      title={ui.crmClosed}
                      aria-label={ui.crmClosed}
                      onClick={async () => {
                        await api.updateCrm(record.id, { status: "closed" });
                        await loadCrm();
                      }}
                    >
                      <CheckCircle size={16} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        {view === "reference" && (
          <section className="referenceGrid">
            {pathologies.map((item) => (
              <article className="referenceItem" key={item.id}>
                <div className="referenceVisual">
                  <img src="/medical_lungs_xray.png" alt="" />
                  <span>{item.title.slice(0, 2).toUpperCase()}</span>
                </div>
                <h2>{item.title}</h2>
                <h3>{ui.findings.pneumonia}</h3>
                <p>{item.signs}</p>
                <h3>{ui.report}</h3>
                <p>{item.report_template}</p>
                {item.references && <small>{item.references}</small>}
              </article>
            ))}
          </section>
        )}

        {view === "analytics" && (
          <section className="analyticsGrid">
            <Metric title={ui.nav.studies} value={analytics?.studies_total ?? 0} />
            <Metric title={ui.statuses.ai_completed} value={analytics?.ai_completed ?? 0} />
            <Metric title={ui.statuses.failed} value={analytics?.ai_failed ?? 0} />
            <Metric title={ui.confidence} value={analytics?.ai_average_confidence ? formatPercent(analytics.ai_average_confidence) : "—"} />
            <div className="toolPanel wide">
              <h2>{ui.status}</h2>
              {Object.entries(analytics?.studies_by_status ?? {}).map(([status, count]) => (
                <div className="metricLine" key={status}>
                  <span>{ui.statuses[status as StudyStatus] ?? status}</span>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
            <div className="toolPanel wide">
              <h2>{ui.feedbackTitle}</h2>
              {Object.entries(analytics?.feedback_by_type ?? {}).map(([type, count]) => (
                <div className="metricLine" key={type}>
                  <span>{ui.feedback[type as FeedbackType] ?? type}</span>
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
                  <th>{ui.confirmedAt}</th>
                  <th>{ui.nav.users}</th>
                  <th>{ui.status}</th>
                  <th>ID</th>
                  <th>{ui.noData}</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((row) => (
                  <tr key={row.id}>
                    <td>{formatDate(row.created_at, lang)}</td>
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
                  <th>{ui.login}</th>
                  <th>{ui.nav.users}</th>
                  <th>{ui.status}</th>
                  <th>Active</th>
                </tr>
              </thead>
              <tbody>
                {users.map((item) => (
                  <tr key={item.id}>
                    <td>{item.login}</td>
                    <td>{item.full_name}</td>
                    <td>{ui.roles[item.role]}</td>
                    <td>{item.is_active ? "yes" : "no"}</td>
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

function LanguageSwitch({ lang, setLang }: { lang: Lang; setLang: (lang: Lang) => void }) {
  return (
    <div className="languageSwitch" aria-label="Language">
      <Languages size={16} />
      {(["kk", "ru", "en"] as Lang[]).map((item) => (
        <button key={item} className={lang === item ? "active" : ""} onClick={() => setLang(item)} type="button">
          {item.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

function ThemeSwitch({ theme, setTheme }: { theme: Theme; setTheme: (theme: Theme) => void }) {
  const nextTheme = theme === "light" ? "dark" : "light";
  return (
    <button
      className="themeSwitch"
      type="button"
      title={theme === "light" ? "Темная тема" : "Светлая тема"}
      aria-label={theme === "light" ? "Темная тема" : "Светлая тема"}
      onClick={() => setTheme(nextTheme)}
    >
      {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
    </button>
  );
}

function NavButton({ active, icon, label, onClick }: { active: boolean; icon: ReactNode; label: string; onClick: () => void }) {
  return (
    <button className={`navButton ${active ? "active" : ""}`} onClick={onClick}>
      {icon}
      {label}
    </button>
  );
}

function IconButton({ active, children, label, onClick }: { active?: boolean; children: ReactNode; label: string; onClick: () => void }) {
  return (
    <button className={`iconButton ${active ? "active" : ""}`} title={label} aria-label={label} onClick={onClick}>
      {children}
    </button>
  );
}

function StatusBadge({ status, labels }: { status: StudyStatus; labels: Record<StudyStatus, string> }) {
  return <span className={`statusBadge ${status}`}>{labels[status]}</span>;
}

function Metric({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="metricCard">
      <span>{title}</span>
      <strong>{value}</strong>
    </div>
  );
}
