/**
 * Type patch for @material-tailwind/react v2 + React 19 compatibility.
 * MT v2 requires placeholder/onPointerEnterCapture/onPointerLeaveCapture
 * as non-optional props, but React 19 changed how these types are handled.
 * The import below turns this into a module augmentation (not ambient declaration).
 */
import "@material-tailwind/react";

declare module "@material-tailwind/react" {
  interface TypographyProps {
    color?: any;
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface ButtonProps {
    color?: any;
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface IconButtonProps {
    color?: any;
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface NavbarProps {
    color?: any;
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface CollapseProps {
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface CardProps {
    color?: any;
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface CardHeaderProps {
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface CardBodyProps {
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
  interface InputProps {
    color?: any;
    placeholder?: unknown;
    onResize?: unknown;
    onResizeCapture?: unknown;
    onPointerEnterCapture?: unknown;
    onPointerLeaveCapture?: unknown;
    crossOrigin?: unknown;
  }
}
