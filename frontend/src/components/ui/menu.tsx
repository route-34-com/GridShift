import * as Menu from '@radix-ui/react-dropdown-menu'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export const MenuRoot = Menu.Root
export const MenuTrigger = Menu.Trigger

export function MenuContent({ children, align = 'end' }: { children: ReactNode; align?: 'start' | 'end' }) {
  return (
    <Menu.Portal>
      <Menu.Content
        align={align}
        sideOffset={6}
        collisionPadding={12}
        className="z-50 min-w-56 rounded-lg border border-border bg-surface p-1 text-sm shadow-xl"
      >
        {children}
      </Menu.Content>
    </Menu.Portal>
  )
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <Menu.Label className="px-2.5 pt-2 pb-1 text-xs font-medium tracking-wide text-muted uppercase">{children}</Menu.Label>
}

export function MenuSeparator() {
  return <Menu.Separator className="my-1 h-px bg-border" />
}

interface MenuItemProps {
  onSelect: () => void
  children: ReactNode
  danger?: boolean
  disabled?: boolean
}

export function MenuItem({ onSelect, children, danger, disabled }: MenuItemProps) {
  return (
    <Menu.Item
      disabled={disabled}
      onSelect={onSelect}
      className={cn(
        'flex cursor-pointer items-center gap-2.5 rounded-md px-2.5 py-2 outline-none select-none data-[disabled]:cursor-not-allowed data-[disabled]:opacity-50 data-[highlighted]:bg-surface-2',
        danger ? 'text-danger' : 'text-fg',
      )}
    >
      {children}
    </Menu.Item>
  )
}
