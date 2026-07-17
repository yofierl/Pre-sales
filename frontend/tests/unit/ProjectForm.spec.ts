import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import ProjectForm from '@/components/ProjectForm.vue'

function mountForm(props = {}) {
  return mount(ProjectForm, {
    props,
    global: {
      plugins: [ElementPlus],
    },
  })
}

describe('ProjectForm', () => {
  it('renders form with form items', () => {
    const wrapper = mountForm()
    const formItems = wrapper.findAll('.el-form-item')
    expect(formItems.length).toBeGreaterThanOrEqual(5)
    wrapper.unmount()
  })

  it('shows project type select', () => {
    const wrapper = mountForm()
    const selects = wrapper.findAll('.el-select')
    expect(selects.length).toBeGreaterThanOrEqual(1)
    wrapper.unmount()
  })

  it('has target price input with suffix', () => {
    const wrapper = mountForm()
    const text = wrapper.text()
    expect(text).toContain('万元')
    wrapper.unmount()
  })

  it('has default quote company value', () => {
    const wrapper = mountForm()
    const inputs = wrapper.findAll('input')
    const companyInput = inputs.find(
      (i) => (i.element as HTMLInputElement).value === '重庆酷小贝软件开发有限公司',
    )
    expect(companyInput).toBeTruthy()
    wrapper.unmount()
  })

  it('has role section with table', () => {
    const wrapper = mountForm()
    // Verify the role management section exists
    const text = wrapper.text()
    expect(text).toContain('角色配置')
    expect(text).toContain('添加角色')
    // el-table renders but content may be virtualized in jsdom
    const table = wrapper.find('.el-table')
    expect(table.exists()).toBe(true)
    wrapper.unmount()
  })

  it('has required role indicators', () => {
    const wrapper = mountForm()
    // Check that role data is set in component (is_required flags exist)
    const vm = wrapper.vm as unknown as { allRoles: Array<{ name: string; is_required: boolean }> }
    const requiredRoles = vm.allRoles.filter((r) => r.is_required)
    expect(requiredRoles.length).toBe(2)
    const requiredNames = requiredRoles.map((r) => r.name)
    expect(requiredNames).toContain('产品')
    expect(requiredNames).toContain('测试')
    wrapper.unmount()
  })

  it('allows opening add role dialog', async () => {
    const wrapper = mountForm()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('添加角色'))
    expect(addBtn).toBeTruthy()
    await addBtn!.trigger('click')
    await wrapper.vm.$nextTick()

    const dialog = wrapper.find('.el-dialog')
    expect(dialog.exists()).toBe(true)
    wrapper.unmount()
  })

  it('renders submit button', () => {
    const wrapper = mountForm()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交'))
    expect(submitBtn).toBeTruthy()
    wrapper.unmount()
  })

  it('sets initial data in inputs when provided', () => {
    const wrapper = mountForm({
      initialData: {
        name: '测试项目',
        project_type: 'legacy',
        target_price_wan: '50',
        quote_company: '测试公司',
        quote_date: '2026-06-01',
        customer_name: '客户A',
      },
    })
    const inputs = wrapper.findAll('input')
    const companyInput = inputs.find(
      (i) => (i.element as HTMLInputElement).value === '测试公司',
    )
    expect(companyInput).toBeTruthy()
    wrapper.unmount()
  })
})