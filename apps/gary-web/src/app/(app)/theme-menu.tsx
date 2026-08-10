"use client";

import {
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from "@gary/ui/components/dropdown-menu";
import { useTheme, type Theme } from "@gary/ui/components/theme-provider";

const CHOICES: { value: Theme; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

export default function ThemeMenu() {
  const { theme, setTheme } = useTheme();

  return (
    <>
      <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
        Theme
      </DropdownMenuLabel>
      <DropdownMenuRadioGroup
        value={theme}
        onValueChange={(value) => setTheme(value as Theme)}
      >
        {CHOICES.map((choice) => (
          <DropdownMenuRadioItem key={choice.value} value={choice.value}>
            {choice.label}
          </DropdownMenuRadioItem>
        ))}
      </DropdownMenuRadioGroup>
    </>
  );
}
