import {
  Activity,
  AlertTriangle,
  BarChart3,
  BookOpen,
  CheckCircle,
  ClipboardList,
  ExternalLink,
  Download,
  FileText,
  ImagePlus,
  Languages,
  Loader2,
  LogIn,
  LogOut,
  MessageCircle,
  Moon,
  Pencil,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  Send,
  SlidersHorizontal,
  Sparkles,
  Stethoscope,
  Sun,
  UploadCloud,
  UserRound,
  Users,
  X,
  ZoomIn,
  ZoomOut
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { api, currentToken, setAuthToken } from "./api";
import type {
  AIAnalysis,
  AnalyticsOverview,
  AssistantMessage,
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
    appSubtitle: "MedAI рентген талдау платформасы",
    loginTitle: "Клиникалық жұмыс орнына кіру",
    loginLead: "DICOM, PNG және JPEG суреттерін MedAI арқылы талдап, дәрігерге арналған қорытынды жобасын жасаңыз.",
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
    overviewHeroTitle: "MedAI радиология ассистенті",
    overviewHeroText:
      "Платформа зерттеуді қабылдайды, суретті тексереді, клиникалық жазбамен бірге AI талдау жасайды, қорытынды жобасын дайындайды және PDF/Word экспортын береді. Деректер локалды компьютерде қалады.",
    startStudy: "Жаңа зерттеу",
    openReference: "Анықтамалық",
    localModel: "MedAI",
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
    modelSelector: "MedAI нұсқасы",
    modelBase: "Негізгі MedAI — салыстыру үшін",
    modelTuned: "Оқытылған MedAI — пневмония / норма",
    modelTunedWarning: "Бұл оқытылған нұсқаны толық пайдалануға және тексеруге болады. Ол әзірге эксперименттік және әрбір нәтижені дәрігер тексеруі тиіс.",
    qualityGateFailed: "Эксперименттік нұсқа",
    preliminaryConclusion: "MedAI алдын ала қорытындысы",
    evidenceTitle: "Көрінетін белгілер",
    localizationUnavailable: "Локализация қолжетімсіз: бұл нұсқа координаттарсыз, тек сурет кластарымен оқытылған.",
    localizationLabel: "Модель белгілеген аймақ",
    resultWithheld: "Сенімділік шегіне жетпегендіктен диагностикалық жауап жасырылды.",
    reportQuarantined: "Сенімділігі төмен AI жобасы жасырылды. Жаңа талдауды іске қосыңыз немесе дәрігер қорытындыны қолмен жазыңыз.",
    confidenceUncalibrated: "Модель бағасы (калибрленбеген)",
    modelCurrent: "Таңдалған нұсқа",
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
    aiWaitingSub: "Сурет пен клиникалық жазба MedAI жүйесіне жіберілді. Бірінші жауап бірнеше секундқа созылуы мүмкін.",
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
    localLora: "MedAI",
    searchPlaceholder: "Іздеу...",
    heatmap: "Heatmap",
    homeBadge: "Кеуде зерттеулеріне арналған MedAI көмекшісі",
    homeTitle: "MedAI кеуде снимогын тез талдайды",
    homeText: "Суретті жүктеңіз, AI қорытынды жобасын алыңыз және дәрігерлік тексеруге дайын жұмыс орнында зерттеуді жүргізіңіз.",
    homePrimary: "Зерттеуді бастау",
    homeSecondary: "Справочник ашу",
    homeCardTitle: "Chest AI",
    homeCardText: "CXR, DICOM, JPEG және PNG талдауы.",
    homeFeatureOne: "AI талдау",
    homeFeatureTwo: "Қорытынды",
    homeFeatureThree: "Локалды дерек",
    heroTitleOne: "Кеуде",
    heroTitleTwo: "Радиология",
    heroMeta: "MedAI",
    heroAction: "Кеуде AI жұмысын бастау",
    heroNote: "MedAI: кеуде суреттерін талдауға, қорытынды жобасын жасауға және дәрігерлік тексеруге арналған радиология жұмыс орны.",
    heroSideText: "Кеуде AI жергілікті қорытындылар, зерттеулер және анықтамалық шолу үшін."
  },
  ru: {
    locale: "ru-RU",
    appName: "MedAI Radiology",
    appSubtitle: "Платформа анализа рентген-снимков MedAI",
    loginTitle: "Вход в клиническое рабочее место",
    loginLead: "Анализируйте DICOM, PNG и JPEG в MedAI и формируйте черновики заключений для врача.",
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
    localModel: "MedAI",
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
    modelSelector: "Версия MedAI",
    modelBase: "Базовая MedAI — для сравнения",
    modelTuned: "Дообученная MedAI — пневмония / норма",
    modelTunedWarning: "Дообученную версию можно полноценно запускать и проверять. Она пока экспериментальная, поэтому каждый результат должен быть проверен врачом.",
    qualityGateFailed: "Экспериментальная версия",
    preliminaryConclusion: "Предварительное заключение MedAI",
    evidenceTitle: "Видимые признаки",
    localizationUnavailable: "Локализация недоступна: эта версия обучена только на классах снимков, без координат очага.",
    localizationLabel: "Область, отмеченная моделью",
    resultWithheld: "Диагностический ответ скрыт, потому что не достигнут порог уверенности.",
    reportQuarantined: "AI-черновик с низкой уверенностью скрыт. Запустите новый анализ или подготовьте заключение врача вручную.",
    confidenceUncalibrated: "Оценка модели (не калибрована)",
    modelCurrent: "Выбранная версия",
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
    aiWaitingSub: "Снимок и клиническая заметка отправлены в MedAI. Первый ответ может занять несколько секунд.",
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
    localLora: "MedAI",
    searchPlaceholder: "Поиск...",
    heatmap: "Теплокарта",
    homeBadge: "Ассистент MedAI для исследований грудной клетки",
    homeTitle: "MedAI помогает разбирать снимки ОГК",
    homeText: "Загрузите снимок, получите AI-черновик заключения и ведите исследование в аккуратном рабочем пространстве врача.",
    homePrimary: "Начать исследование",
    homeSecondary: "Открыть справочник",
    homeCardTitle: "Chest AI",
    homeCardText: "Анализ CXR, DICOM, JPEG и PNG.",
    homeFeatureOne: "AI-анализ",
    homeFeatureTwo: "Заключение",
    homeFeatureThree: "Локальные данные",
    heroTitleOne: "Грудная",
    heroTitleTwo: "Радиология",
    heroMeta: "MedAI",
    heroAction: "Начать работу с MedAI",
    heroNote: "MedAI — рабочее место для анализа снимков грудной клетки, подготовки черновиков заключений и врачебной проверки.",
    heroSideText: "AI для локальных заключений, исследований и справочника ОГК."
  },
  en: {
    locale: "en-US",
    appName: "MedAI Radiology",
    appSubtitle: "MedAI chest imaging workspace",
    loginTitle: "Sign in to the clinical workspace",
    loginLead: "Analyze DICOM, PNG and JPEG images with MedAI and prepare clinician-reviewed report drafts.",
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
    overviewHeroTitle: "MedAI radiology assistant",
    overviewHeroText:
      "The platform receives a study, validates the image, analyzes it together with clinical notes, prepares a report draft, and exports PDF/Word. Data stays on this computer.",
    startStudy: "New study",
    openReference: "Reference",
    localModel: "MedAI",
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
    modelSelector: "MedAI version",
    modelBase: "Base MedAI — comparison only",
    modelTuned: "Fine-tuned MedAI — pneumonia / normal",
    modelTunedWarning: "The fine-tuned version is fully available for testing. It remains experimental, so every result must be reviewed by a clinician.",
    qualityGateFailed: "Experimental version",
    preliminaryConclusion: "Preliminary MedAI conclusion",
    evidenceTitle: "Visible findings",
    localizationUnavailable: "Localization is unavailable: this version was trained on image classes only, without lesion coordinates.",
    localizationLabel: "Region marked by the model",
    resultWithheld: "The diagnostic output is withheld because it did not reach the confidence threshold.",
    reportQuarantined: "The low-confidence AI draft is withheld. Run a new analysis or prepare the clinician report manually.",
    confidenceUncalibrated: "Model estimate (uncalibrated)",
    modelCurrent: "Selected version",
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
    aiWaitingSub: "The image and clinical note were sent to MedAI. The first response can take a few seconds.",
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
    localLora: "MedAI",
    searchPlaceholder: "Search...",
    heatmap: "Heatmap",
    homeBadge: "MedAI assistant for chest imaging",
    homeTitle: "MedAI helps read chest studies",
    homeText: "Upload an image, get an AI report draft, and review the study in a clean clinician workspace.",
    homePrimary: "Start study",
    homeSecondary: "Open reference",
    homeCardTitle: "Chest AI",
    homeCardText: "Analysis for CXR, DICOM, JPEG and PNG.",
    homeFeatureOne: "AI analysis",
    homeFeatureTwo: "Report draft",
    homeFeatureThree: "Local data",
    heroTitleOne: "Chest",
    heroTitleTwo: "Radiology",
    heroMeta: "MedAI",
    heroAction: "Start with MedAI",
    heroNote: "MedAI is a radiology workspace for chest imaging, draft reports, and clinician review.",
    heroSideText: "Chest AI for local reports, studies, and reference review."
  }
} as const;

const WORKSPACE_UI = {
  kk: {
    crmDepartment: "Пациенттермен жұмыс бөлімі",
    crmDepartmentHint: "Ортақ міндеттер, жауаптылар, зерттеулер және байланыс тарихы",
    crmNew: "Жаңа карточка",
    crmBoard: "Бөлім тақтасы",
    crmSearch: "Пациент немесе жазба бойынша іздеу",
    crmAssignees: "Жауапты қызметкерлер",
    crmStudies: "Зерттеулермен байланыс",
    crmTimeline: "Әрекеттер тарихы",
    crmAddNote: "Таймлайнға жазба қосу",
    crmReadOnly: "Тек оқу режимі",
    crmTeamAccess: "Бөлімге қолжетімді",
    studyJournal: "Зерттеу журналы",
    recordsShown: "жазба көрсетілді",
    referenceTitle: "Клиникалық анықтамалық",
    referenceHint: "Белгілер, қорытынды үлгілері және тексеру ескертпелері",
    referenceSearch: "Патологияны іздеу",
    examples: "Бақылау нүктелері",
    details: "Толық карточка",
    assistantTitle: "MedAI көмекшісі",
    assistantSubtitle: "Клиникалық жұмыс пен CRM үшін",
    assistantHello: "Сәлем! Зерттеу мәтінін құрылымдауға, терминді түсіндіруге немесе келесі әрекетті дайындауға көмектесемін.",
    assistantPlaceholder: "MedAI-ға сұрақ жазыңыз...",
    assistantAsk: "Жіберу",
    assistantContext: "Таңдалған зерттеу контексті қосылған",
    assistantSuggestions: ["Қорытынды құрылымын ұсын", "CRM келесі қадамын жаз", "Терминді түсіндір"],
    medaiStatus: "MedAI дайын",
    advancedFilters: "Қосымша сүзгілер",
    reportPreview: "Дәрігерлік қорытынды",
    editReport: "Өңдеу",
    closeEditor: "Редакторды жабу",
    reportEmpty: "Алдымен MedAI жобасын жасаңыз",
    feedbackCompact: "Дәлсіздік туралы хабарлау",
    lowConfidenceTitle: "Қолмен тексеру қажет"
  },
  ru: {
    crmDepartment: "Отдел работы с пациентами",
    crmDepartmentHint: "Общие задачи, ответственные, исследования и история контактов",
    crmNew: "Новая карточка",
    crmBoard: "Доска отдела",
    crmSearch: "Поиск по пациенту или записи",
    crmAssignees: "Ответственные сотрудники",
    crmStudies: "Связанные исследования",
    crmTimeline: "История действий",
    crmAddNote: "Добавить заметку в таймлайн",
    crmReadOnly: "Режим просмотра",
    crmTeamAccess: "Доступно отделу",
    studyJournal: "Журнал исследований",
    recordsShown: "записей показано",
    referenceTitle: "Клинический справочник",
    referenceHint: "Признаки, шаблоны заключений и точки врачебной проверки",
    referenceSearch: "Найти патологию",
    examples: "Контрольные точки",
    details: "Открыть полную карточку",
    assistantTitle: "Помощник MedAI",
    assistantSubtitle: "Для клинической работы и CRM",
    assistantHello: "Здравствуйте! Помогу структурировать описание, объяснить термин или подготовить следующее действие по пациенту.",
    assistantPlaceholder: "Спросите MedAI...",
    assistantAsk: "Отправить",
    assistantContext: "Учтён контекст выбранного исследования",
    assistantSuggestions: ["Предложи структуру заключения", "Сформулируй следующий шаг CRM", "Объясни термин"],
    medaiStatus: "MedAI готов",
    advancedFilters: "Дополнительные фильтры",
    reportPreview: "Врачебное заключение",
    editReport: "Редактировать",
    closeEditor: "Закрыть редактор",
    reportEmpty: "Сначала сформируйте черновик MedAI",
    feedbackCompact: "Сообщить о неточности",
    lowConfidenceTitle: "Нужна ручная проверка"
  },
  en: {
    crmDepartment: "Patient coordination department",
    crmDepartmentHint: "Shared tasks, owners, linked studies, and contact history",
    crmNew: "New card",
    crmBoard: "Department board",
    crmSearch: "Search patient or note",
    crmAssignees: "Responsible team",
    crmStudies: "Linked studies",
    crmTimeline: "Activity timeline",
    crmAddNote: "Add a timeline note",
    crmReadOnly: "Read-only mode",
    crmTeamAccess: "Department access",
    studyJournal: "Study journal",
    recordsShown: "records shown",
    referenceTitle: "Clinical reference",
    referenceHint: "Signs, report templates, and clinician review points",
    referenceSearch: "Find a pathology",
    examples: "Review points",
    details: "Open full card",
    assistantTitle: "MedAI assistant",
    assistantSubtitle: "For clinical work and CRM",
    assistantHello: "Hello! I can help structure a report, explain a term, or prepare the next patient action.",
    assistantPlaceholder: "Ask MedAI...",
    assistantAsk: "Send",
    assistantContext: "Selected study context included",
    assistantSuggestions: ["Suggest a report structure", "Draft the next CRM step", "Explain a term"],
    medaiStatus: "MedAI ready",
    advancedFilters: "More filters",
    reportPreview: "Clinical report",
    editReport: "Edit",
    closeEditor: "Close editor",
    reportEmpty: "Generate a MedAI draft first",
    feedbackCompact: "Report an inaccuracy",
    lowConfidenceTitle: "Manual review required"
  }
} as const;

type LocalizedPathology = {
  title: string;
  label: string;
  signs: string;
  report_template: string;
  references: string;
  examples?: string;
};

const PATHOLOGY_REFERENCE: Record<Lang, Record<string, LocalizedPathology>> = {
  kk: {
    normal: {
      title: "Норма",
      label: "Қалыпты",
      signs: "Өкпе алаңдарында жаңа ошақты-инфильтративті өзгерістер жоқ. Түбірлер құрылымды. Плевралық синустар бос. Ортаңғы көлеңке кеңеймеген.",
      report_template: "ОГК рентгенограммасында жаңа ошақты-инфильтративті өзгерістер анықталмайды. Плевралық синустар бос. Жүрек-қантамыр көлеңкесінде айқын ерекшелік жоқ.",
      references: "ОГК сипаттауға арналған жергілікті хаттамалар."
    },
    pneumonia: {
      title: "Пневмония",
      label: "Қабыну инфильтрациясы",
      signs: "Өкпенің бір бөлігінде немесе сегментінде ауа мөлшерінің төмендеуі, инфильтративті көлеңкелер, өкпе суретінің күшеюі және плевра реакциясы болуы мүмкін.",
      report_template: "Өкпе тінінде инфильтративті өзгерістерге тән рентгенологиялық белгілер анықталады. Клиникалық-зертханалық деректермен салыстыру және дәрігер тағайындаса динамикалық бақылау ұсынылады.",
      references: "Клиникалық ұсынымдар және мекеменің жергілікті хаттамалары."
    },
    pleural_effusion: {
      title: "Плевралық сұйықтық",
      label: "Плевра қуысындағы сұйықтық",
      signs: "Гемиторакстың төменгі бөлімдерінде күңгірттену, қабырға-диафрагмалық синустың тегістелуі немесе жабылуы, сұйықтықтың доға тәрізді жоғарғы шекарасы.",
      report_template: "Плевра қуысында сұйықтыққа күмәнді рентгенологиялық белгілер бар. Көлемі мен жағын дәрігер сурет бойынша нақтылауы керек.",
      references: "Сәулелік диагностика бойынша жергілікті хаттамалар."
    },
    pneumothorax: {
      title: "Пневмоторакс",
      label: "Плевра қуысындағы ауа",
      signs: "Висцералды плевра сызығы, одан шеткері өкпе суретінің болмауы, өкпенің спадение белгілері және кернеулі түрінде ортаңғы көлеңкенің ығысуы мүмкін.",
      report_template: "Пневмотораксқа күмәнді белгілер анықталады. Суретті және пациенттің клиникалық жағдайын шұғыл дәрігерлік бағалау қажет.",
      references: "Мекеменің шұғыл көмек хаттамалары."
    },
    atelectasis: {
      title: "Ателектаз",
      label: "Өкпе көлемінің төмендеуі",
      signs: "Көлемі төмендеген тығыздалу аймағы, үлесаралық саңылаулардың ығысуы, түбірдің жоғары немесе төмен тартылуы, көрші бөлімдердің компенсаторлық гипервоздуштылығы.",
      report_template: "Ателектаз немесе өкпе тінінің бір бөлігінің көлемі төмендеу белгілері болуы мүмкін. Дәрігерлік верификация және клиникалық деректермен салыстыру қажет.",
      references: "ОГК бойынша жергілікті хаттамалар."
    }
  },
  ru: {
    normal: {
      title: "Норма",
      label: "Нормальная картина",
      signs: "Легочные поля без свежих очагово-инфильтративных изменений. Корни структурны. Плевральные синусы свободны. Средостение не расширено.",
      report_template: "На рентгенограмме ОГК свежих очагово-инфильтративных изменений не выявлено. Плевральные синусы свободны. Сердечно-сосудистая тень без грубых особенностей.",
      references: "Локальные протоколы описания ОГК."
    },
    pneumonia: {
      title: "Пневмония",
      label: "Воспалительная инфильтрация",
      signs: "Локальное или сегментарное снижение пневматизации, инфильтративные тени, усиление легочного рисунка, возможна реакция плевры.",
      report_template: "Определяются рентгенологические признаки инфильтративных изменений в легочной ткани. Рекомендована клинико-лабораторная корреляция и контроль в динамике по назначению врача.",
      references: "Клинические рекомендации и локальные протоколы учреждения."
    },
    pleural_effusion: {
      title: "Плевральный выпот",
      label: "Жидкость в плевральной полости",
      signs: "Затемнение нижних отделов гемиторакса, сглаживание или облитерация реберно-диафрагмального синуса, дугообразная верхняя граница жидкости.",
      report_template: "Рентгенологические признаки жидкости в плевральной полости. Объем и сторона требуют подтверждения врачом по изображению.",
      references: "Локальные протоколы лучевой диагностики."
    },
    pneumothorax: {
      title: "Пневмоторакс",
      label: "Воздух в плевральной полости",
      signs: "Висцеральная плевральная линия, отсутствие легочного рисунка периферичнее линии, возможное спадение легкого и смещение средостения при напряженном варианте.",
      report_template: "Имеются признаки, подозрительные на пневмоторакс. Требуется срочная врачебная оценка изображения и клинического состояния пациента.",
      references: "Экстренные протоколы учреждения."
    },
    atelectasis: {
      title: "Ателектаз",
      label: "Снижение объема легочной ткани",
      signs: "Участок уплотнения со снижением объема, смещение междолевых щелей, подтягивание корня, компенсаторная гипервоздушность соседних отделов.",
      report_template: "Возможны признаки ателектаза или снижения объема участка легочной ткани. Необходима врачебная верификация и сопоставление с клиническими данными.",
      references: "Локальные протоколы ОГК."
    }
  },
  en: {
    normal: {
      title: "Normal",
      label: "Normal chest study",
      signs: "No fresh focal infiltrative changes in the lung fields. Hila are structured. Pleural sinuses are clear. No mediastinal widening.",
      report_template: "No fresh focal infiltrative changes are seen on the chest radiograph. Pleural sinuses are clear. Cardiomediastinal silhouette shows no gross abnormality.",
      references: "Local chest radiography reporting protocols."
    },
    pneumonia: {
      title: "Pneumonia",
      label: "Inflammatory infiltration",
      signs: "Focal or segmental loss of aeration, infiltrative opacities, increased lung markings, and possible pleural reaction.",
      report_template: "Radiographic signs of infiltrative change in the lung tissue are present. Clinical and laboratory correlation and follow-up as directed by the clinician are recommended.",
      references: "Clinical recommendations and local institutional protocols."
    },
    pleural_effusion: {
      title: "Pleural effusion",
      label: "Fluid in the pleural space",
      signs: "Basal hemithorax opacity, blunting or obliteration of the costophrenic angle, and a meniscus-shaped upper fluid margin.",
      report_template: "Radiographic signs suggest fluid in the pleural cavity. Volume and side should be confirmed by the clinician on the image.",
      references: "Local diagnostic imaging protocols."
    },
    pneumothorax: {
      title: "Pneumothorax",
      label: "Air in the pleural space",
      signs: "Visceral pleural line, absent peripheral lung markings, possible lung collapse, and mediastinal shift in a tension variant.",
      report_template: "Findings are suspicious for pneumothorax. Urgent clinician assessment of the image and patient condition is required.",
      references: "Institutional emergency protocols."
    },
    atelectasis: {
      title: "Atelectasis",
      label: "Reduced lung volume",
      signs: "A dense area with volume loss, fissure displacement, hilar retraction, and compensatory hyperinflation of adjacent regions.",
      report_template: "Findings may represent atelectasis or focal lung volume loss. Clinician verification and correlation with clinical data are required.",
      references: "Local chest imaging protocols."
    }
  }
};

function localizedPathology(item: Pathology, lang: Lang): LocalizedPathology {
  return PATHOLOGY_REFERENCE[lang][item.slug] ?? {
    title: item.title,
    label: item.slug.replace(/_/g, " ").toUpperCase(),
    signs: item.signs,
    report_template: item.report_template,
    references: item.references ?? "",
    examples: item.examples ?? ""
  };
}

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

type ClinicalReportSection = { title: string; body: string };

function parseClinicalReport(value: string | null | undefined, lang: Lang): ClinicalReportSection[] {
  const text = (value || "").trim();
  if (!text) return [];
  const headingPattern = /^(Описание|Заключение|Рекомендации|Сипаттама|Қорытынды|Ұсыныстар|Findings|Impression|Recommendations):\s*$/gim;
  const matches = [...text.matchAll(headingPattern)];
  if (!matches.length) return [{ title: UI[lang].report, body: text }];
  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length;
    const end = index + 1 < matches.length ? matches[index + 1].index ?? text.length : text.length;
    return { title: match[1], body: text.slice(start, end).trim() };
  }).filter((section) => section.body);
}

function canEditFinal(user: User | null) {
  return Boolean(user && ["radiologist", "expert"].includes(user.role));
}

function canUseClinicalFlow(user: User | null) {
  return Boolean(user && ["admin", "radiologist", "physician", "expert"].includes(user.role));
}

function canViewCrm(user: User | null) {
  return Boolean(user && ["admin", "radiologist", "physician", "expert", "analyst"].includes(user.role));
}

function canManageCrm(user: User | null) {
  return Boolean(user && ["admin", "radiologist", "physician", "expert"].includes(user.role));
}

export default function App() {
  const [lang, setLang] = useState<Lang>(() => (localStorage.getItem("medicine_lang") as Lang) || "kk");
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("medicine_theme") as Theme) || "light");
  const ui = UI[lang];
  const workspaceUi = WORKSPACE_UI[lang];

  const [user, setUser] = useState<User | null>(null);
  const [booting, setBooting] = useState(true);
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [view, setView] = useState<View>("studies");
  const [showLoginPanel, setShowLoginPanel] = useState(false);
  const [busy, setBusy] = useState(false);
  const [modelVariant, setModelVariant] = useState<"base" | "pneumonia_v1">("pneumonia_v1");
  const [aiRunningStudyId, setAiRunningStudyId] = useState<number | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const [studies, setStudies] = useState<Study[]>([]);
  const [selectedStudy, setSelectedStudy] = useState<Study | null>(null);
  const [aiResults, setAiResults] = useState<AIAnalysis[]>([]);
  const [report, setReport] = useState<Report | null>(null);
  const [finalText, setFinalText] = useState("");
  const [reportEditing, setReportEditing] = useState(false);
  const [pathologies, setPathologies] = useState<Pathology[]>([]);
  const [audit, setAudit] = useState<AuditLog[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsOverview | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [doctors, setDoctors] = useState<User[]>([]);
  const [crmRecords, setCrmRecords] = useState<CRMRecord[]>([]);
  const [crmSearch, setCrmSearch] = useState("");
  const [crmSelectedId, setCrmSelectedId] = useState<number | null>(null);
  const [crmActivity, setCrmActivity] = useState("");
  const [referenceSearch, setReferenceSearch] = useState("");
  const [crmForm, setCrmForm] = useState({
    patient_code: "DEMO-001",
    contact_type: "consultation",
    status: "active",
    priority: "normal",
    summary: "",
    note: "",
    next_step: "",
    due_at: "",
    participant_ids: [] as number[],
    linked_study_ids: [] as number[]
  });

  const [filters, setFilters] = useState({ search: "", status: "", study_type: "", date_from: "", date_to: "" });
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
  const [imageAspect, setImageAspect] = useState(4 / 3);

  const latestAI = aiResults[0] ?? null;
  const latestAIWithheld = Boolean(latestAI?.hidden_due_low_confidence);
  const selectedStudyAiBusy = Boolean(selectedStudy && aiRunningStudyId === selectedStudy.id);
  const reportSections = useMemo(() => parseClinicalReport(finalText || report?.ai_draft_text, lang), [finalText, lang, report?.ai_draft_text]);
  const selectedCrm = crmRecords.find((record) => record.id === crmSelectedId) ?? null;
  const filteredPathologies = useMemo(() => {
    const query = referenceSearch.trim().toLocaleLowerCase();
    if (!query) return pathologies;
    return pathologies.filter((item) => {
      const localized = localizedPathology(item, lang);
      return `${localized.title} ${localized.label} ${localized.signs}`.toLocaleLowerCase().includes(query);
    });
  }, [lang, pathologies, referenceSearch]);

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
    const loaders: Promise<unknown>[] = [loadStudies(), loadPathologies(), loadDoctors()];
    if (canViewCrm(nextUser)) loaders.push(loadCrm());
    await Promise.all(loaders);
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

  async function loadCrm(search = crmSearch) {
    const data = await api.listCrm(search.trim() ? { search: search.trim() } : {});
    setCrmRecords(data);
    setCrmSelectedId((current) => current && data.some((record) => record.id === current) ? current : null);
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
        due_at: "",
        participant_ids: [],
        linked_study_ids: []
      });
      await loadCrm();
      flash(ui.crmSaved);
    } catch (err) {
      fail(err);
    } finally {
      setBusy(false);
    }
  }

  async function addCrmActivity(event: FormEvent) {
    event.preventDefault();
    if (!selectedCrm || !crmActivity.trim()) return;
    setBusy(true);
    try {
      await api.addCrmActivity(selectedCrm.id, crmActivity.trim());
      setCrmActivity("");
      await loadCrm();
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
        const nextReport = await api.getReport(studyId, lang);
        setReport(nextReport);
        setFinalText(nextReport.final_text || nextReport.ai_draft_text || "");
        setReportEditing(false);
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
          analysis = await api.runAI(uploaded.id, true, true, lang, modelVariant);
          setAiResults([analysis]);
          if (analysis.status === "failed") {
            throw new Error(analysis.error_message || ui.aiFailed);
          }
          const draft = await api.createDraft(uploaded.id, lang);
          setReport(draft);
          setFinalText(draft.ai_draft_text || draft.final_text || "");
          setReportEditing(false);
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
      const analysis = await api.runAI(selectedStudy.id, true, auto, lang, modelVariant);
      setAiResults([analysis]);
      if (analysis.status === "failed") {
        throw new Error(analysis.error_message || ui.aiFailed);
      }
      if (analysis.status === "completed") {
        const nextReport = await api.createDraft(selectedStudy.id, lang);
        setReport(nextReport);
        setFinalText(nextReport.ai_draft_text || nextReport.final_text || "");
        setReportEditing(false);
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
      setReportEditing(false);
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
      setReportEditing(false);
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
          <div className="photonBrand">
            <span className="brandSignal" aria-hidden="true">
              <Activity size={18} />
            </span>
            <span className="photonBrandCopy">
              <strong>MedAI</strong>
              <small>Chest intelligence</small>
            </span>
          </div>
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
            <div className="heroEyebrow">
              <span className="liveDot" />
              <span>{ui.localModel}</span>
              <b>CXR / DICOM</b>
            </div>
            <h1>
              <span>{ui.heroTitleOne}</span>
              <span>
                {ui.heroTitleTwo} <b>MedAI</b>
              </span>
            </h1>
            <div className="photonMeta">
              <span>{ui.heroMeta}</span>
              <i />
              <span>2026</span>
            </div>
            <div className="photonActionRow">
              <button className="photonRoundButton" type="button" onClick={() => setShowLoginPanel(true)} aria-label={ui.signIn}>
                <Play size={18} />
              </button>
              <span>{ui.heroAction}</span>
            </div>
            <p className="photonNote">{ui.heroNote}</p>
            <div className="heroSpecGrid" aria-label={ui.heroMeta}>
              <div>
                <span>01</span>
                <strong>DICOM</strong>
                <small>{ui.homeFeatureThree}</small>
              </div>
              <div>
                <span>02</span>
                <strong>MedAI</strong>
                <small>{ui.homeFeatureOne}</small>
              </div>
              <div>
                <span>03</span>
                <strong>MD review</strong>
                <small>{ui.homeFeatureTwo}</small>
              </div>
            </div>
          </div>

          <div className="photonVisual dashboardVisual" aria-hidden="true">
            <div className="scanOrbit orbitOne" />
            <div className="scanOrbit orbitTwo" />
            <img src="/neon_lungs_hero_transparent.png" alt="" />
            <div className="lungAxis">
              <span>R</span>
              <i />
              <span>L</span>
            </div>
            <div className="visualTelemetry telemetryTop">
              <small>VIEW</small>
              <strong>PA • CXR</strong>
            </div>
            <div className="visualTelemetry telemetryBottom">
              <small>ASSIST</small>
              <strong>MedAI</strong>
            </div>
          </div>

          <aside className="photonSide dashboardSide">
            <p>
              <strong>{ui.localModel}</strong>
            </p>
            <span />
            <p>{ui.heroSideText}</p>
            <div className="sideStatus">
              <span />
              <b>MedAI</b>
              <small>ONLINE</small>
            </div>
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
          <span className="brandSymbol" aria-hidden="true">
            <Activity size={21} />
          </span>
          <span className="brandCopy">
            <strong>MedAI</strong>
            <small>{ui.roles[user.role]}</small>
          </span>
        </div>
        <nav>
          <NavButton active={view === "studies"} icon={<Activity size={18} />} label={ui.nav.studies} onClick={() => setView("studies")} />
          {canViewCrm(user) && (
            <NavButton
              active={view === "crm"}
              icon={<ClipboardList size={18} />}
              label={ui.nav.crm}
              onClick={async () => {
                setView("crm");
                await loadCrm();
              }}
            />
          )}
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
          <div className="topbarActions">
            <span className="systemChip">
              <i />
              {workspaceUi.medaiStatus}
            </span>
            <button className="ghostButton" onClick={() => loadInitial()} disabled={busy}>
              <RefreshCw size={18} />
              {ui.refresh}
            </button>
          </div>
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
                <div className="filterGrid filterGridPrimary">
                  <input
                    className="filterSearch"
                    placeholder={`${ui.searchPlaceholder} ${ui.patientCode.toLocaleLowerCase()}`}
                    value={filters.search}
                    onChange={(event) => setFilters({ ...filters, search: event.target.value })}
                  />
                  <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
                    <option value="">{ui.allStatuses}</option>
                    {Object.entries(ui.statuses).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <details className="advancedFilters">
                  <summary><SlidersHorizontal size={16} />{workspaceUi.advancedFilters}</summary>
                  <div>
                    <input placeholder={ui.type} value={filters.study_type} onChange={(event) => setFilters({ ...filters, study_type: event.target.value })} />
                    <input type="date" value={filters.date_from} onChange={(event) => setFilters({ ...filters, date_from: event.target.value })} />
                    <input type="date" value={filters.date_to} onChange={(event) => setFilters({ ...filters, date_to: event.target.value })} />
                  </div>
                </details>
                <button className="ghostButton" onClick={() => loadStudies()} disabled={busy}>
                  <Search size={18} />
                  {ui.apply}
                </button>
              </div>

              <div className="studyJournalHeader">
                <span>{workspaceUi.studyJournal}</span>
                <small>{studies.length} {workspaceUi.recordsShown}</small>
              </div>
              <div className="studyList" aria-label={workspaceUi.studyJournal}>
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
                        <div
                          className="viewerImageFrame"
                          style={{
                            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                            width: `min(92%, ${Math.round(515 * imageAspect)}px)`,
                            aspectRatio: imageAspect
                          }}
                        >
                          <img
                            src={previewUrl}
                            alt=""
                            onLoad={(event) => {
                              const image = event.currentTarget;
                              if (image.naturalWidth && image.naturalHeight) {
                                setImageAspect(image.naturalWidth / image.naturalHeight);
                              }
                            }}
                            style={{
                              filter: `brightness(${brightness}%) contrast(${contrast}%)`
                            }}
                          />
                          {latestAI?.localization_bbox && !latestAIWithheld && (
                            <div
                              className="localizationBox"
                              style={{
                                left: `${latestAI.localization_bbox[0] * 100}%`,
                                top: `${latestAI.localization_bbox[1] * 100}%`,
                                width: `${(latestAI.localization_bbox[2] - latestAI.localization_bbox[0]) * 100}%`,
                                height: `${(latestAI.localization_bbox[3] - latestAI.localization_bbox[1]) * 100}%`
                              }}
                            >
                              <span>{ui.localizationLabel}</span>
                            </div>
                          )}
                        </div>
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
                    {latestAI?.localization_status === "unavailable_class_only" && (
                      <div className="localizationHint">
                        <AlertTriangle size={16} />
                        <span>{ui.localizationUnavailable}</span>
                      </div>
                    )}
                  </section>

                  <section className="clinicalGrid clinicianOutputGrid">
                    <div className="toolPanel analysisPanel">
                      <div className="panelHeader">
                        <h2>{ui.aiAnalysis}</h2>
                        <Activity size={20} />
                      </div>
                      <div className="clinicalNotice">
                        <AlertTriangle size={18} />
                        <span>{ui.disclaimer}</span>
                      </div>
                      <div className="modelSelector">
                        <label htmlFor="medai-model-variant">{ui.modelSelector}</label>
                        <select
                          id="medai-model-variant"
                          value={modelVariant}
                          onChange={(event) => setModelVariant(event.target.value as "base" | "pneumonia_v1")}
                          disabled={busy || selectedStudyAiBusy}
                        >
                          <option value="pneumonia_v1">{ui.modelTuned}</option>
                          <option value="base">{ui.modelBase}</option>
                        </select>
                      </div>
                      {modelVariant === "pneumonia_v1" && (
                        <div className="modelQualityWarning">
                          <AlertTriangle size={17} />
                          <div><strong>{ui.qualityGateFailed}</strong><span>{ui.modelTunedWarning}</span></div>
                        </div>
                      )}
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
                        <div className={`clinicalAiSummary ${latestAIWithheld ? "needsReview" : latestAI.model_quality_status === "experimental" ? "experimental" : ""}`}>
                          <small>
                            {latestAI.model_quality_status === "experimental"
                              ? ui.qualityGateFailed
                              : latestAI.hidden_due_low_confidence
                                ? workspaceUi.lowConfidenceTitle
                                : ui.aiDone}
                          </small>
                          <strong>
                            {latestAIWithheld
                              ? ui.resultWithheld
                              : latestAI.predicted_class
                                ? ui.findings[latestAI.predicted_class]
                                : ui.classUnknown}
                          </strong>
                          {(
                            <>
                              <div className="confidenceTrack"><i style={{ width: `${Math.max(3, (latestAI.confidence ?? 0) * 100)}%` }} /></div>
                              <span>{ui.confidenceUncalibrated}: {formatPercent(latestAI.confidence)}</span>
                            </>
                          )}
                          {latestAI.warning && <p className="analysisWarningText">{latestAI.warning}</p>}
                          <span className="modelVersionLine">
                            {ui.modelCurrent}: {latestAI.model_version === "medai-pneumonia-v1" ? ui.modelTuned : ui.modelBase}
                          </span>
                        </div>
                      )}
                      <button
                        className="ghostButton"
                        onClick={createDraft}
                        disabled={busy || !latestAI || latestAIWithheld || !latestAI.predicted_class}
                      >
                        <FileText size={18} />
                        {ui.createDraft}
                      </button>
                    </div>

                    <div className="toolPanel reportPanel">
                      <div className="panelHeader">
                        <div><small>{ui.aiDraft}</small><h2>{workspaceUi.reportPreview}</h2></div>
                        <FileText size={20} />
                      </div>
                      {latestAI && (
                        <div className={`aiConclusionCard ${latestAIWithheld ? "withheld" : ""}`}>
                          <span>{ui.preliminaryConclusion}</span>
                          <p>
                            {latestAIWithheld
                              ? latestAI.warning || ui.resultWithheld
                              : latestAI.ai_text
                                || (latestAI.predicted_class ? ui.findings[latestAI.predicted_class] : ui.classUnknown)}
                          </p>
                          {!latestAIWithheld && (latestAI.evidence?.length ?? 0) > 0 && (
                            <div className="aiEvidenceList">
                              <strong>{ui.evidenceTitle}</strong>
                              <ul>{latestAI.evidence?.map((item) => <li key={item}>{item}</li>)}</ul>
                            </div>
                          )}
                        </div>
                      )}
                      {reportEditing ? (
                        <label className="reportEditor">
                          {ui.finalText}
                          <textarea value={finalText} onChange={(event) => setFinalText(event.target.value)} rows={14} autoFocus />
                        </label>
                      ) : latestAIWithheld && !report?.confirmed_at ? (
                        <div className="reportEmptyState reportQuarantined">
                          <AlertTriangle size={22} />
                          <span>{ui.reportQuarantined}</span>
                        </div>
                      ) : reportSections.length ? (
                        <div className="clinicalReportPreview">
                          {reportSections.map((section) => (
                            <section key={section.title}>
                              <span>{section.title}</span>
                              <p>{section.body}</p>
                            </section>
                          ))}
                        </div>
                      ) : <div className="reportEmptyState"><FileText size={22} /><span>{workspaceUi.reportEmpty}</span></div>}
                      <div className="buttonRow">
                        {canEditFinal(user) && (
                          <button className="ghostButton" onClick={() => setReportEditing((value) => !value)} disabled={busy}>
                            <Pencil size={17} />
                            {reportEditing ? workspaceUi.closeEditor : workspaceUi.editReport}
                          </button>
                        )}
                        {reportEditing && <button className="ghostButton" onClick={saveReport} disabled={busy || !finalText}><Save size={18} />{ui.save}</button>}
                        <button className="primaryButton" onClick={confirmReport} disabled={busy || latestAIWithheld || !canEditFinal(user) || !finalText}>
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

                    <div className="toolPanel feedbackPanel">
                      <details>
                        <summary><span><Send size={17} />{workspaceUi.feedbackCompact}</span><Plus size={16} /></summary>
                        <div>
                          <select value={feedbackType} onChange={(event) => setFeedbackType(event.target.value as FeedbackType)}>
                            {Object.entries(ui.feedback).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                          </select>
                          <textarea value={feedbackComment} onChange={(event) => setFeedbackComment(event.target.value)} rows={3} placeholder={ui.feedbackComment} />
                          <button className="ghostButton" onClick={sendFeedback} disabled={busy || !latestAI}><Send size={18} />{ui.send}</button>
                        </div>
                      </details>
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
          <section className="crmWorkspace">
            <div className="crmHero">
              <div>
                <span>{workspaceUi.crmDepartmentHint}</span>
                <h2>{workspaceUi.crmDepartment}</h2>
                <small className="accessPill">
                  <Users size={14} />
                  {canManageCrm(user) ? workspaceUi.crmTeamAccess : workspaceUi.crmReadOnly}
                </small>
              </div>
              <div className="crmVitals">
                <div><strong>{crmRecords.filter((record) => record.status === "active").length}</strong><span>{ui.crmActive}</span></div>
                <div><strong>{crmRecords.filter((record) => record.status === "follow_up").length}</strong><span>{ui.crmFollowUp}</span></div>
                <div><strong>{crmRecords.filter((record) => record.priority === "urgent" && record.status !== "closed").length}</strong><span>{ui.crmUrgent}</span></div>
              </div>
            </div>

            <div className="crmToolbar">
              <label>
                <Search size={18} />
                <input
                  value={crmSearch}
                  onChange={(event) => setCrmSearch(event.target.value)}
                  onKeyDown={(event) => event.key === "Enter" && loadCrm()}
                  placeholder={workspaceUi.crmSearch}
                />
              </label>
              <button className="ghostButton" onClick={() => loadCrm()} disabled={busy}>
                <Search size={17} /> {ui.apply}
              </button>
            </div>

            <div className={`crmOperations ${canManageCrm(user) ? "" : "viewerOnly"}`}>
              {canManageCrm(user) && (
                <form className="crmComposer" onSubmit={saveCrmRecord}>
                  <div className="panelHeader">
                    <div><small>{workspaceUi.crmNew}</small><h2>{ui.crmSave}</h2></div>
                    <Plus size={20} />
                  </div>
                  <div className="crmFormGrid">
                    <label>{ui.patientCode}<input value={crmForm.patient_code} onChange={(event) => setCrmForm({ ...crmForm, patient_code: event.target.value })} /></label>
                    <label>{ui.crmContact}
                      <select value={crmForm.contact_type} onChange={(event) => setCrmForm({ ...crmForm, contact_type: event.target.value })}>
                        <option value="consultation">Consultation</option><option value="call">Call</option><option value="follow_up">Follow-up</option><option value="report">Report</option>
                      </select>
                    </label>
                    <label>{ui.status}
                      <select value={crmForm.status} onChange={(event) => setCrmForm({ ...crmForm, status: event.target.value })}>
                        <option value="active">{ui.crmActive}</option><option value="follow_up">{ui.crmFollowUp}</option><option value="closed">{ui.crmClosed}</option>
                      </select>
                    </label>
                    <label>{ui.crmPriority}
                      <select value={crmForm.priority} onChange={(event) => setCrmForm({ ...crmForm, priority: event.target.value })}>
                        <option value="normal">{ui.crmNormal}</option><option value="high">{ui.crmHigh}</option><option value="urgent">{ui.crmUrgent}</option>
                      </select>
                    </label>
                  </div>
                  <label>{ui.crmSummary}<input value={crmForm.summary} onChange={(event) => setCrmForm({ ...crmForm, summary: event.target.value })} /></label>
                  <label>{ui.crmNote}<textarea value={crmForm.note} onChange={(event) => setCrmForm({ ...crmForm, note: event.target.value })} rows={4} /></label>
                  <div className="crmFormGrid two">
                    <label>{ui.crmNextStep}<input value={crmForm.next_step} onChange={(event) => setCrmForm({ ...crmForm, next_step: event.target.value })} /></label>
                    <label>{ui.crmDue}<input type="datetime-local" value={crmForm.due_at} onChange={(event) => setCrmForm({ ...crmForm, due_at: event.target.value })} /></label>
                  </div>
                  <details className="crmPicker">
                    <summary>{workspaceUi.crmAssignees}<span>{crmForm.participant_ids.length}</span></summary>
                    <div>
                      {doctors.map((doctor) => (
                        <label key={doctor.id} className={crmForm.participant_ids.includes(doctor.id) ? "selected" : ""}>
                          <input type="checkbox" checked={crmForm.participant_ids.includes(doctor.id)} onChange={() => setCrmForm({
                            ...crmForm,
                            participant_ids: crmForm.participant_ids.includes(doctor.id)
                              ? crmForm.participant_ids.filter((id) => id !== doctor.id)
                              : [...crmForm.participant_ids, doctor.id]
                          })} />
                          {doctor.full_name}
                        </label>
                      ))}
                    </div>
                  </details>
                  <details className="crmPicker compact">
                    <summary>{workspaceUi.crmStudies}<span>{crmForm.linked_study_ids.length}</span></summary>
                    <div>
                      {studies.slice(0, 12).map((study) => (
                        <label key={study.id} className={crmForm.linked_study_ids.includes(study.id) ? "selected" : ""}>
                          <input type="checkbox" checked={crmForm.linked_study_ids.includes(study.id)} onChange={() => setCrmForm({
                            ...crmForm,
                            linked_study_ids: crmForm.linked_study_ids.includes(study.id)
                              ? crmForm.linked_study_ids.filter((id) => id !== study.id)
                              : [...crmForm.linked_study_ids, study.id]
                          })} />
                          {study.patient_code} · {study.study_type}
                        </label>
                      ))}
                    </div>
                  </details>
                  <button className="primaryButton" disabled={busy || !crmForm.patient_code || !crmForm.summary || !crmForm.note}>
                    {busy ? <Loader2 size={18} className="spinIcon" /> : <Save size={18} />} {ui.crmSave}
                  </button>
                </form>
              )}

              <div className="crmDepartmentBoard">
                <div className="panelHeader"><div><small>{crmRecords.length} {workspaceUi.recordsShown}</small><h2>{workspaceUi.crmBoard}</h2></div><ClipboardList size={20} /></div>
                {!crmRecords.length ? (
                  <div className="emptyState large visualEmpty crmVisualEmpty"><img src="/medical_lungs_xray.png" alt="" /><span>{ui.crmEmpty}</span></div>
                ) : (
                  <div className="crmKanban">
                    {(["active", "follow_up", "closed"] as const).map((column) => (
                      <section className={`crmLane ${column}`} key={column}>
                        <header><span>{column === "active" ? ui.crmActive : column === "follow_up" ? ui.crmFollowUp : ui.crmClosed}</span><b>{crmRecords.filter((record) => record.status === column).length}</b></header>
                        <div>
                          {crmRecords.filter((record) => record.status === column).map((record) => (
                            <button className={`crmCard ${record.priority} ${record.id === crmSelectedId ? "selected" : ""}`} key={record.id} onClick={() => setCrmSelectedId(record.id)}>
                              <div className="crmCardTop"><span>{record.patient_code}</span><b>{record.priority === "urgent" ? ui.crmUrgent : record.priority === "high" ? ui.crmHigh : ui.crmNormal}</b></div>
                              <h3>{record.summary}</h3><p>{record.note}</p>
                              <div className="crmCardMeta"><span>{record.next_step || "—"}</span><span>{formatDate(record.due_at || record.updated_at, lang)}</span></div>
                              <div className="crmCardFooter">
                                <span className="avatarStack">{(record.participants ?? []).slice(0, 3).map((member) => <i key={member.id} title={member.full_name}>{member.full_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</i>)}</span>
                                <small>{(record.studies ?? []).length ? `${record.studies.length} CXR` : record.created_by.full_name}</small>
                              </div>
                            </button>
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                )}

                {selectedCrm && (
                  <aside className="crmDetail">
                    <div className="crmDetailHeader"><div><small>{selectedCrm.patient_code}</small><h3>{selectedCrm.summary}</h3></div><button className="iconButton" onClick={() => setCrmSelectedId(null)} aria-label="Close"><X size={17} /></button></div>
                    <div className="crmDetailGrid">
                      <div><span>{workspaceUi.crmAssignees}</span><strong>{(selectedCrm.participants ?? []).map((member) => member.full_name).join(", ") || "—"}</strong></div>
                      <div><span>{ui.crmNextStep}</span><strong>{selectedCrm.next_step || "—"}</strong></div>
                    </div>
                    {!!(selectedCrm.studies ?? []).length && <div className="linkedStudies"><span>{workspaceUi.crmStudies}</span>{selectedCrm.studies.map((study) => <button key={study.id} onClick={() => openStudy(study.id)}>{study.accession_number}<ExternalLink size={13} /></button>)}</div>}
                    <div className="crmTimeline"><h4>{workspaceUi.crmTimeline}</h4>{(selectedCrm.activities ?? []).slice(0, 8).map((activity) => <div key={activity.id}><i /><p>{activity.content}<small>{activity.author.full_name} · {formatDate(activity.created_at, lang)}</small></p></div>)}</div>
                    {canManageCrm(user) && <form className="crmActivityForm" onSubmit={addCrmActivity}><input value={crmActivity} onChange={(event) => setCrmActivity(event.target.value)} placeholder={workspaceUi.crmAddNote} /><button className="primaryButton" disabled={busy || !crmActivity.trim()}><Send size={16} /></button></form>}
                  </aside>
                )}
              </div>
            </div>
          </section>
        )}

        {view === "reference" && (
          <section className="referenceWorkspace">
            <div className="referenceHero">
              <div><small>MedAI · CXR</small><h2>{workspaceUi.referenceTitle}</h2><p>{workspaceUi.referenceHint}</p></div>
              <label><Search size={18} /><input value={referenceSearch} onChange={(event) => setReferenceSearch(event.target.value)} placeholder={workspaceUi.referenceSearch} /></label>
              <strong>{filteredPathologies.length}<span>{ui.nav.reference}</span></strong>
            </div>
            <div className="referenceGrid">
              {filteredPathologies.map((item) => {
                const localized = localizedPathology(item, lang);
                return (
                  <article className="referenceItem" key={item.id}>
                    <div className="referenceVisual">
                      <img src="/medical_lungs_xray.png" alt="" />
                      <span>{localized.title.slice(0, 2).toUpperCase()}</span>
                    </div>
                    <div className="referenceCardCopy">
                      <small>{localized.label}</small><h2>{localized.title}</h2><p>{localized.signs}</p>
                      <details>
                        <summary>{workspaceUi.details}<ExternalLink size={14} /></summary>
                        <h3>{ui.report}</h3><p>{localized.report_template}</p>
                        {(localized.examples || item.examples) && <><h3>{workspaceUi.examples}</h3><p>{localized.examples || item.examples}</p></>}
                        {localized.references && <small className="referenceSource">{localized.references}</small>}
                      </details>
                    </div>
                  </article>
                );
              })}
            </div>
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
      <MedAIAssistant lang={lang} studyId={selectedStudy?.id} />
    </div>
  );
}

function MedAIAssistant({ lang, studyId }: { lang: Lang; studyId?: number }) {
  const labels = WORKSPACE_UI[lang];
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<AssistantMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    const nextMessages: AssistantMessage[] = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setAssistantError("");
    try {
      const response = await api.chatAssistant(nextMessages, lang, studyId);
      setMessages([...nextMessages, { role: "assistant", content: response.message }]);
    } catch (err) {
      setAssistantError(err instanceof Error ? err.message : "MedAI unavailable");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={`medaiAssistant ${open ? "open" : ""}`}>
      {open && (
        <section className="assistantPanel" aria-label={labels.assistantTitle}>
          <header>
            <span className="assistantMark"><Sparkles size={18} /></span>
            <div><strong>{labels.assistantTitle}</strong><small><i />{labels.assistantSubtitle}</small></div>
            <button onClick={() => setOpen(false)} aria-label="Close"><X size={18} /></button>
          </header>
          <div className="assistantMessages">
            {!messages.length && <div className="assistantWelcome"><Sparkles size={20} /><p>{labels.assistantHello}</p><div>{labels.assistantSuggestions.map((suggestion) => <button key={suggestion} onClick={() => setInput(suggestion)}>{suggestion}</button>)}</div></div>}
            {messages.map((message, index) => (
              <div className={`assistantMessage ${message.role}`} key={`${message.role}-${index}`}>
                <span>{message.role === "assistant" ? <Sparkles size={14} /> : <UserRound size={14} />}</span>
                <p>{message.content}</p>
              </div>
            ))}
            {loading && <div className="assistantTyping"><i /><i /><i /></div>}
            {assistantError && <div className="assistantError">{assistantError}</div>}
          </div>
          {studyId && <div className="assistantContext"><Activity size={14} />{labels.assistantContext}</div>}
          <form onSubmit={submit}>
            <textarea rows={2} value={input} onChange={(event) => setInput(event.target.value)} placeholder={labels.assistantPlaceholder} onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }} />
            <button disabled={loading || !input.trim()} aria-label={labels.assistantAsk}>{loading ? <Loader2 size={18} className="spinIcon" /> : <Send size={18} />}</button>
          </form>
        </section>
      )}
      <button className="assistantTrigger" onClick={() => setOpen((value) => !value)} aria-label={labels.assistantTitle}>
        {open ? <X size={22} /> : <MessageCircle size={22} />}
        {!open && <span>MedAI</span>}
      </button>
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
