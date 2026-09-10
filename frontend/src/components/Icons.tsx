/* 목업(design canvas)에서 쓴 것과 같은 스트로크 아이콘 세트를 React 컴포넌트로 옮긴 것.
 * 전부 20x20 viewBox, stroke=currentColor 이라 color css로 제어 가능.
 */
import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function base(props: IconProps, children: React.ReactNode) {
  const { size = 18, ...rest } = props;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 20 20"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {children}
    </svg>
  );
}

export const MaterialsIcon = (p: IconProps) =>
  base(
    p,
    <>
      <path d="M10 3l7 3.5-7 3.5-7-3.5L10 3z" />
      <path d="M3 10.5l7 3.5 7-3.5" />
      <path d="M3 14l7 3.5 7-3.5" />
    </>
  );

export const QuizIcon = (p: IconProps) =>
  base(
    p,
    <>
      <path d="M10 5.5c-1.3-1-3-1.5-5.5-1.5v11c2.5 0 4.2.5 5.5 1.5" />
      <path d="M10 5.5c1.3-1 3-1.5 5.5-1.5v11c-2.5 0-4.2.5-5.5 1.5" />
      <path d="M10 5.5v11" />
    </>
  );

export const AnalysisIcon = (p: IconProps) =>
  base(
    p,
    <>
      <path d="M4 16.5V10" />
      <path d="M10 16.5V4.5" />
      <path d="M16 16.5v-6.5" />
      <path d="M2.5 16.5h15" />
    </>
  );

export const SettingsIcon = (p: IconProps) =>
  base(
    p,
    <>
      <circle cx="10" cy="10" r="2.6" />
      <path d="M10 3.5v1.6M10 14.9v1.6M16.5 10h-1.6M5.1 10H3.5M14.6 5.4l-1.1 1.1M6.5 13.5l-1.1 1.1M14.6 14.6l-1.1-1.1M6.5 6.5L5.4 5.4" />
    </>
  );

export const UploadIcon = (p: IconProps) =>
  base(
    p,
    <>
      <path d="M10 13.5V5" />
      <path d="M6.5 8.5L10 5l3.5 3.5" />
      <path d="M4.5 13.5v1.2A2.3 2.3 0 0 0 6.8 17h6.4a2.3 2.3 0 0 0 2.3-2.3v-1.2" />
    </>
  );

export const FileIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.5, ...p },
    <>
      <path
        d="M5.5 2.5h6l3 3V17a.5.5 0 0 1-.5.5h-8.5a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z"
        strokeLinejoin="round"
      />
      <path d="M11.5 2.5V5.5a.5.5 0 0 0 .5.5h3" strokeLinejoin="round" />
    </>
  );

export const CheckCircleIcon = (p: IconProps) =>
  base(
    { strokeWidth: 2, ...p },
    <>
      <path d="M4.5 10.3l3.3 3.3L15.5 6" />
    </>
  );

export const CheckIcon = CheckCircleIcon;

export const XIcon = (p: IconProps) =>
  base(
    { strokeWidth: 2.2, ...p },
    <>
      <path d="M6 6l8 8M14 6l-8 8" />
    </>
  );

export const ClockIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.8, ...p },
    <>
      <circle cx="10" cy="10" r="7" />
      <path d="M10 6.3V10l2.4 1.5" />
    </>
  );

export const ChevronRightIcon = (p: IconProps) =>
  base(
    { strokeWidth: 2, ...p },
    <>
      <path d="M7.5 4.5L13 10l-5.5 5.5" />
    </>
  );

export const RefreshIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.8, ...p },
    <>
      <path d="M15.5 8A5.5 5.5 0 1 0 13.9 12" />
      <path d="M15.5 4v4h-4" />
    </>
  );

export const TargetIcon = (p: IconProps) =>
  base(
    { strokeWidth: 2, ...p },
    <>
      <circle cx="10" cy="10" r="3" />
      <circle cx="10" cy="10" r="7" />
    </>
  );

export const ZapIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.8, ...p },
    <>
      <path d="M10 3l8 14H2z" />
      <path d="M10 8.3v3.4" />
      <circle cx="10" cy="14.2" r="0.2" fill="currentColor" />
    </>
  );

export const ShuffleIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.8, ...p },
    <>
      <path d="M4 6h8.5l-2-2M16 14H7.5l2 2" />
    </>
  );

export const QuestionIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.8, ...p },
    <>
      <circle cx="10" cy="10" r="7.3" />
      <path d="M7.8 7.8a2.2 2.2 0 1 1 3.1 3c-.7.6-1 1-1 1.9" />
      <circle cx="10" cy="14" r="0.2" fill="currentColor" />
    </>
  );

export const SourceIcon = (p: IconProps) =>
  base(
    { strokeWidth: 1.6, size: 10, ...p },
    <path d="M5 3h7l4 4v10a.5.5 0 0 1-.5.5h-11A.5.5 0 0 1 4 17V3.5a.5.5 0 0 1 .5-.5z" />
  );
