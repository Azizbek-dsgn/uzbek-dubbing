/* global require */
const { localFileSystem } = require('uxp').storage;
const { Project } = require('premierepro');

document.getElementById('import').addEventListener('click', async () => {
  const status = document.getElementById('status');
  try {
    const file = await localFileSystem.getFileForOpening({ types: ['srt'] });
    if (!file) return;
    const project = await Project.getActiveProject();
    if (!project) throw new Error('Avval Premiere loyihasini oching.');
    const root = await project.getRootItem();
    const imported = await project.importFiles([file.nativePath], true, root, false);
    if (!imported) throw new Error('SRT import qilinmadi.');
    status.textContent = 'SRT loyiha ichiga import qilindi. Caption track uchun uni timeline’ga torting.';
  } catch (error) {
    status.textContent = 'Xato: ' + error.message;
  }
});
